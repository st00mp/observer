from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from typing import Optional
from crewai import Agent, Task, Crew, Process
from langchain.tools import DuckDuckGoSearchRun

# Load environment variables
load_dotenv()

app = FastAPI(title="Writer Agent Service")

# Setup Jinja2 templates
template_env = Environment(loader=FileSystemLoader("templates"))

class GenerateRequest(BaseModel):
    title: str
    content: str
    style: str = "serious"  # serious, sarcastic, troll
    max_length: int = 280  # Twitter character limit

class GenerateResponse(BaseModel):
    content: str
    style: str

@app.get("/")
async def read_root():
    return {"status": "Writer Agent is running"}

@app.post("/generate", response_model=GenerateResponse)
async def generate_post(request: GenerateRequest):
    """Generate a post using CrewAI agents or fallback to templates"""
    try:
        # Try to use CrewAI for generation
        content = await generate_with_crewai(request)
        return {"content": content, "style": request.style}
    except Exception as e:
        # Fallback to template-based generation
        return {"content": generate_with_template(request), "style": f"{request.style}_fallback"}

async def generate_with_crewai(request: GenerateRequest):
    """Generate content using CrewAI agents"""
    
    # Define tools
    search_tool = DuckDuckGoSearchRun()
    
    # Define a writer agent based on the style
    personality_traits = {
        "serious": "professional, informative, straightforward",
        "sarcastic": "witty, sarcastic, critical, humorous",
        "troll": "exaggerated, shocking, provocative, internet-culture savvy"
    }
    
    # Get the appropriate personality
    personality = personality_traits.get(request.style, personality_traits["serious"])
    
    # Create the writer agent
    writer = Agent(
        role="Social Media Content Creator",
        goal=f"Create engaging {request.style} content for social media about news",
        backstory=f"""You are a {personality} social media expert who creates 
                    viral posts that capture attention while staying within character limits.""",
        verbose=True,
        allow_delegation=False
    )
    
    # Create the task
    writing_task = Task(
        description=f"""
        Based on the title: "{request.title}" 
        and content: "{request.content[:300]}..."
        
        Create a {request.style} social media post that:
        1. Is attention-grabbing and shareable
        2. Uses appropriate tone for {request.style} style
        3. Includes relevant hashtags
        4. Stays within {request.max_length} characters
        5. Includes emojis where appropriate
        
        Your post should be ready to publish without any additional editing.
        """,
        agent=writer,
        tools=[search_tool]
    )
    
    # Create the crew
    crew = Crew(
        agents=[writer],
        tasks=[writing_task],
        verbose=True,
        process=Process.sequential
    )
    
    # Execute the crew's task
    result = crew.kickoff()
    
    # Ensure the result is within the max length
    if len(result) > request.max_length:
        result = result[:request.max_length-3] + "..."
        
    return result

def generate_with_template(request: GenerateRequest):
    """Fallback method to generate content using templates"""
    # Select template based on style
    template_name = f"{request.style}.j2"
    
    # Default to serious if template doesn't exist
    if template_name not in ["serious.j2", "sarcastic.j2", "troll.j2"]:
        template_name = "serious.j2"
        
    try:
        template = template_env.get_template(template_name)
    except Exception:
        # If template loading fails, use serious as default
        template = template_env.get_template("serious.j2")
        
    # Render template with data
    content = template.render(
        title=request.title,
        content=request.content
    )
    
    # Ensure content is within max length
    if len(content) > request.max_length:
        content = content[:request.max_length-3] + "..."
        
    return content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
