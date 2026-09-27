# Architecture Decision Records

## 1. Framework choice
* Date: 2026-09-27
* Status: Decided
* Context: Framework choice is the core of the code that is to be used. All though most code is to be written with AI it is very important that I use langagues that I am familiar with for both checking AI written code before accepting it and debugging it
* Decision: The main programming language of the code will be done in python as I am not knowledgeable in any others to make them acceptable choices. For the backend I will be using Flask, HTML/CSS for frontend and jinja for passing data through.
* Alternatives considered: Django - I've worked with it a bit before but it's much heavier than required. FastAPI - this was my biggest this-or-that, I ended up going with Flask because of the built in support with jinja. Other languages such as C for backend or JavaScript for front end - I am simply not comfortable enough in either to use them over a python-based framework
* Consequences: Jinja uses server-side rendering meaning that it won't get live updates with data. This is fine because of the app but it could be a negative in the future for a social module in the app such as seeing new posts from others, follow requests and messages

---

## 2. Domain modularisation
* Date: 
* Status: Decided
* Context:
* Decision:
* Alternatives considered:
* Consequences:

---

## 3. SQLite data model
* Date: 
* Status: Decided
* Context:
* Decision:
* Alternatives considered:
* Consequences:

---

## 4. Testing approach
* Date: 
* Status: Decided
* Context:
* Decision:
* Alternatives considered:
* Consequences:

---

## 5. What is deliberately not built
* Date: 
* Status: Decided
* Context:
* Decision:
* Alternatives considered:
* Consequences: