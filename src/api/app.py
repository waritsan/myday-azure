from fastapi import FastAPI
from pydantic import BaseModel
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.azure/myday/.env"))

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        credential = DefaultAzureCredential()
        keyvault_url = os.getenv("AZURE_KEY_VAULT_ENDPOINT")
        secret_client = SecretClient(vault_url=keyvault_url, credential=credential)
        
        user_endpoint = secret_client.get_secret("AZURE-AI-PROJECT-ENDPOINT").value
        project_client = AIProjectClient(
            endpoint=user_endpoint,
            credential=credential,
        )

        agent_name = secret_client.get_secret("AGENT-NAME").value
        model_deployment_name = secret_client.get_secret("MODEL-DEPLOYMENT-NAME").value

        # Creates an agent, bumps the agent version if parameters have changed
        agent = project_client.agents.create_version(  
            agent_name=agent_name,
            definition=PromptAgentDefinition(
                    model=model_deployment_name,
                    instructions="You are a helpful AI assistant. Respond to user queries appropriately.",
                ),
        )

        openai_client = project_client.get_openai_client()

        # Reference the agent to get a response
        response = openai_client.responses.create(
            input=[{"role": "user", "content": request.message}],
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )

        return {"response": response.output_text}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)