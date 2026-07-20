# CRUK Middlelayer

This is a standalone FastAPI microservice designed to handle CRUK-specific operations and bespoke data that need to be strictly separated from the eventual HDRUK mirror database. 

### Purpose
Currently, this microservice acts as the holding area for the **Team Request pipeline**. When users request to set up a new team space on the frontend, their form submissions (along with Base64 encoded logos) are validated, rate-limited, and securely persisted into this middlelayer database for admin review.

### Running Locally
To spin up the service locally on port 8002, use the following command:

```bash
uvicorn main:app --reload --port 8002
```