# HR-Leave-Agent-on-Azure
HR Leave Policy AI Chatbot using Azure AI Foundry, GPT-5-mini &amp; Azure AI Search

 # Leave Desk — HR Agent Web App

A minimal Flask web app with a chat UI that talks to your Azure AI Foundry
agent (`HRAgent`), using the exact SDK pattern from the Foundry "Use" tab.

```
hr-agent-webapp/
├── app.py                 # Flask backend, calls the Foundry agent
├── requirements.txt
├── Dockerfile              # optional, for container-based deploy
├── .env.example             # local dev config template
├── templates/index.html
└── static/style.css, script.js
```

---

## Part 1 — Run it locally first

1. Install Python 3.11+ and the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli).

2. Open a terminal in the `hr-agent-webapp` folder:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Log in to Azure so `DefaultAzureCredential` can authenticate as *you*:
   ```bash
   az login
   ```
   Your account needs permission to call the agent in the Foundry project
   (see the role note in Part 3 — the same role applies to your own user
   for local testing).

4. Copy the env file and adjust if needed (defaults already match your agent):
   ```bash
   cp .env.example .env
   ```

5. Run it:
   ```bash
   python app.py
   ```
   Open **http://localhost:8000** and chat with your agent.

---

## Part 2 — Deploy to Azure App Service (recommended, simplest)

App Service will run this app for you with a public URL, without you
managing servers or containers.

### 2.1 Create the Azure resources

Run these one at a time in a terminal with the Azure CLI logged in
(`az login`):

```bash
# Pick a globally-unique app name, e.g. hrleave-yourcompany
APP_NAME="hrleave-yourcompany"
RESOURCE_GROUP="rg-hr-agent"
LOCATION="eastus"

az group create --name $RESOURCE_GROUP --location $LOCATION

az appservice plan create \
  --name plan-hr-agent \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan plan-hr-agent \
  --name $APP_NAME \
  --runtime "PYTHON:3.11"
```

### 2.2 Set the startup command

App Service needs to know how to launch the Flask app with gunicorn:

```bash
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --startup-file "gunicorn --bind 0.0.0.0:8000 --timeout 120 app:app"
```

### 2.3 Set your app's configuration (no secrets needed — see Part 3 for auth)

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    AI_FOUNDRY_ENDPOINT="https://thokebhushan13594-3522-resource.services.ai.azure.com/api/projects/thokebhushan13594-3522" \
    AI_FOUNDRY_AGENT_NAME="HRAgent" \
    AI_FOUNDRY_AGENT_VERSION="3" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### 2.4 Deploy the code

From inside the `hr-agent-webapp` folder:

```bash
az webapp up \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan plan-hr-agent \
  --sku B1 \
  --runtime "PYTHON:3.11"
```

This zips your folder, uploads it, and builds it on Azure. It can take a
few minutes the first time.

Your app will be live at:
```
https://<APP_NAME>.azurewebsites.net
```

---

## Part 3 — Give the web app permission to call your agent (important!)

Locally you authenticated as *you* (`az login`). In Azure, the app needs
its own identity to call the Foundry project — this is done with a
**Managed Identity**, so you never store any API keys or secrets.

1. **Turn on Managed Identity for the web app:**
   ```bash
   az webapp identity assign \
     --resource-group $RESOURCE_GROUP \
     --name $APP_NAME
   ```
   This prints a `principalId` — copy it (or just remember the app name,
   you can search by name in the next step).

2. **Grant that identity access to your AI Foundry project:**
   - Go to the [Azure AI Foundry portal](https://ai.azure.com) → open your
     project → **Management center** (or **Settings**) → **Access control (IAM)**.
   - Click **Add role assignment**.
   - Choose the role that lets it invoke agents/models. In most Foundry
     projects this is **"Azure AI User"** (sometimes shown as
     **"Cognitive Services User"** or **"Azure AI Developer"** depending on
     how your project's RBAC is set up — if unsure, check the project's own
     Access control page for a role literally named for using/invoking
     agents, since Foundry's exact role names have changed over recent
     releases).
   - Under "Assign access to", choose **Managed identity**, then select
     your Function/Web App and pick `$APP_NAME`.
   - Save.

3. Give it a minute or two for the role assignment to propagate, then
   reload your app's URL and try chatting.

> If you get a 401/403 error from the agent call, it's almost always this
> step — double check the role assignment is on the *web app's* managed
> identity, not your own user account.

---

## Part 4 (optional) — Deploy as a container instead

If you'd rather ship a Docker image (e.g. via Azure Container Registry):

```bash
# Build and push
az acr create --resource-group $RESOURCE_GROUP --name hrleaveacr --sku Basic
az acr login --name hrleaveacr
docker build -t hrleaveacr.azurecr.io/hr-agent-webapp:v1 .
docker push hrleaveacr.azurecr.io/hr-agent-webapp:v1

# Point App Service at the image
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan plan-hr-agent \
  --name $APP_NAME \
  --deployment-container-image-name hrleaveacr.azurecr.io/hr-agent-webapp:v1
```

You'll still need to do the Managed Identity + role assignment step above
(Part 3) — the identity/authentication story doesn't change with Docker.

---

## Checking logs if something goes wrong

```bash
az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME
```

This streams live logs, including any Python errors from `app.py` — most
issues show up here (missing role assignment, wrong agent name/version, etc).

## Updating the app later

After editing files, redeploy with:
```bash
az webapp up --name $APP_NAME --resource-group $RESOURCE_GROUP
```
