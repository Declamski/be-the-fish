# Be the Fish

A logbook web app for scuba divers, freedivers and spearfishers. Flask + SQLite, single
process. Design decisions are in [ADR.md](ADR.md), and AI use is in [AI_USAGE.md](AI_USAGE.md).

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Declamski/be-the-fish.git
cd be-the-fish
uv sync
```

## Run

```bash
uv run python app.py
```

Then open http://localhost:8000 and sign up. No other setup is needed: the database and
its tables are created automatically on first start.

## Configuration

All settings are optional environment variables (no `.env` file needed).

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port to listen on (the app binds to `0.0.0.0`) |
| `DATA_DIR` | `./data` | Folder for the database, created if missing |
| `SECRET_KEY` | `dev-secret-key-change-me` | Signs the login cookie; set your own outside local use |

The SQLite database is stored at **`$DATA_DIR/divelog.db`**.

```bash
PORT=9000 DATA_DIR=/tmp/divelog uv run python app.py
```

## Tests and coverage

```bash
uv run pytest --cov=dives --cov=sites --cov=feed --cov-report=term-missing
```

Result: **128 passed, 74% total coverage.** The business logic (`service.py` files and
the CSV importer) is at 95–100%. The thin `routes.py` files make up most of the
uncovered lines; see ADR-4.

## Initial Azure setup (one time, before the first deploy)

Done once by hand, following the course's A2 deployment guide. After this only the
pipeline changes anything in Azure. Run it in **bash** (type `bash` first on a Mac: zsh
breaks the `repo:...:ref:...` subject in step 6). No password is written in this file:
`read -s` asks for them without showing or saving them.

```bash
bash
PREFIX=dvandam-ieu2024
RG=rg-$PREFIX
LOCATION=italynorth                 # must be on the subscription's allowed-regions list
UI_STORAGE=dvandamieu2024ui
SQL_SERVER=$PREFIX-sql
GH_REPO=Declamski/be-the-fish
```

**1. Subscription and region** (own Azure for Students subscription)
```bash
az login
az account set --subscription "Azure for Students"
az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv
```

**2. Providers and resource group**
```bash
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace $p --wait
done
az group create --name $RG --location $LOCATION
```

**3. UI: Storage static website** (its web endpoint is the public URL)
```bash
az storage account create --name $UI_STORAGE --resource-group $RG --location $LOCATION \
  --kind StorageV2 --sku Standard_LRS
az storage blob service-properties update --account-name $UI_STORAGE \
  --static-website --index-document index.html
UI_URL=$(az storage account show --name $UI_STORAGE --resource-group $RG \
  --query primaryEndpoints.web -o tsv)
echo $UI_URL
```

**4. SQL server and two serverless databases** (free offer; passwords: letters and digits
only, 12+ characters with upper case, lower case and digits)
```bash
read -s -p "SQL admin password: " SQL_ADMIN_PASSWORD; echo
az sql server create --name $SQL_SERVER --resource-group $RG --location $LOCATION \
  --admin-user sqladmin --admin-password "$SQL_ADMIN_PASSWORD"
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER \
  --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
for svc in dives sites; do
  az sql db create --resource-group $RG --server $SQL_SERVER --name $PREFIX-$svc-db \
    --edition GeneralPurpose --compute-model Serverless --family Gen5 \
    --min-capacity 0.5 --capacity 1 --backup-storage-redundancy Local \
    --use-free-limit true --free-limit-exhaustion-behavior AutoPause
done
```
One contained user per database, which can only reach its own database. The firewall is
opened to this computer only while doing it. `sqlcmd` runs from the SQL Server Docker image.
```bash
read -s -p "dives DB password: " DIVES_DB_PASSWORD; echo
read -s -p "sites DB password: " SITES_DB_PASSWORD; echo
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER \
  --name setup-my-ip --start-ip-address $MY_IP --end-ip-address $MY_IP
for svc in dives sites; do
  if [ $svc = dives ]; then PW=$DIVES_DB_PASSWORD; else PW=$SITES_DB_PASSWORD; fi
  docker run --rm --platform linux/amd64 -e SQLCMDPASSWORD="$SQL_ADMIN_PASSWORD" \
    --entrypoint /opt/mssql-tools18/bin/sqlcmd mcr.microsoft.com/mssql/server:2022-latest \
    -S $SQL_SERVER.database.windows.net -U sqladmin -d $PREFIX-$svc-db -b -Q "
      CREATE USER ${svc}_user WITH PASSWORD = '$PW';
      ALTER ROLE db_ddladmin ADD MEMBER ${svc}_user;
      ALTER ROLE db_datareader ADD MEMBER ${svc}_user;
      ALTER ROLE db_datawriter ADD MEMBER ${svc}_user;"
done
az sql server firewall-rule delete --resource-group $RG --server $SQL_SERVER --name setup-my-ip
```

**5. Container Apps** (placeholder image until the first deploy; min 0, max 1 replica)
```bash
az containerapp env create --name $PREFIX-env --resource-group $RG --location $LOCATION
for svc in dives sites; do
  az containerapp create --name $PREFIX-$svc --resource-group $RG --environment $PREFIX-env \
    --image mcr.microsoft.com/k8se/quickstart:latest --target-port 8000 --ingress external \
    --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi
done
```
Environment variables and secrets (`DATABASE_URL`, `SECRET_KEY`, `SITES_URL`, `CORS_ORIGIN`)
are set by the CD workflow on every deploy, from GitHub secrets.

**6. The pipeline's identity** (managed identity + GitHub OIDC, no stored Azure password)
```bash
az identity create --name $PREFIX-github --resource-group $RG --location $LOCATION
CLIENT_ID=$(az identity show --name $PREFIX-github --resource-group $RG --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --name $PREFIX-github --resource-group $RG --query principalId -o tsv)
RG_ID=$(az group show --name $RG --query id -o tsv)
az role assignment create --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal --role Contributor --scope $RG_ID
# GitHub may send the subject with names or with numeric ids, so both are registered.
az identity federated-credential create --name github-main --identity-name $PREFIX-github \
  --resource-group $RG --issuer https://token.actions.githubusercontent.com \
  --subject "repo:${GH_REPO}:ref:refs/heads/main" --audiences api://AzureADTokenExchange
az identity federated-credential create --name github-main-ids --identity-name $PREFIX-github \
  --resource-group $RG --issuer https://token.actions.githubusercontent.com \
  --subject "repo:Declamski@189633300/be-the-fish@1387287070:ref:refs/heads/main" \
  --audiences api://AzureADTokenExchange
```

**7. GitHub secrets and variables** (needs `gh auth login`)
```bash
gh secret set AZURE_CLIENT_ID --repo $GH_REPO --body "$CLIENT_ID"
gh secret set AZURE_TENANT_ID --repo $GH_REPO --body "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID --repo $GH_REPO --body "$(az account show --query id -o tsv)"
gh secret set DIVES_DB_PASSWORD --repo $GH_REPO --body "$DIVES_DB_PASSWORD"
gh secret set SITES_DB_PASSWORD --repo $GH_REPO --body "$SITES_DB_PASSWORD"
gh secret set SECRET_KEY --repo $GH_REPO --body "$(openssl rand -hex 32)"
gh variable set PREFIX --repo $GH_REPO --body $PREFIX
gh variable set RESOURCE_GROUP --repo $GH_REPO --body $RG
gh variable set UI_STORAGE --repo $GH_REPO --body $UI_STORAGE
```

**8. Read access for the professors**
```bash
for p in amartini@faculty.ie.edu bserra@faculty.ie.edu; do
  az role assignment create --assignee $p --role Reader --scope $RG_ID
done
```
