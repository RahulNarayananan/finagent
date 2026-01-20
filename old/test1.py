import streamlit as st
import base64
from io import BytesIO
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# --- CONFIGURATION ---
VISION_MODEL = "llama3.2-vision" # The model that "sees"
AGENT_MODEL = "llama3.1"         # The model that "thinks" & uses tools

st.set_page_config(page_title="Multimodal Agent", layout="wide")
st.title("🤖 Agent with Eyes & Memory")

# --- 1. DEFINE TOOLS ---
@tool
def save_to_file(filename: str, content: str) -> str:
    """
    Saves text content to a specific file. 
    ALWAYS use this tool when the user asks to save, write, or store something.
    """
    try:
        with open(filename, "w", encoding='utf-8') as f:
            f.write(content)
        return f"✅ Successfully saved content to {filename}"
    except Exception as e:
        return f"❌ Error saving file: {str(e)}"

# --- 2. SETUP THE AGENT ---
# We use the text model (Llama 3.1) for the agent because it follows instructions better
llm_agent = ChatOllama(model=AGENT_MODEL, temperature=0)
tools = [save_to_file]

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. You have a tool to save files. Use it whenever requested."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm_agent, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 3. HELPER: IMAGE PROCESSING ---
def get_image_base64(uploaded_file):
    """Convert uploaded file to base64 string for Ollama."""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_image(image_b64):
    """Use a Vision model to describe the image into text."""
    llm_vision = ChatOllama(model=VISION_MODEL, temperature=0)
    msg = HumanMessage(
        content="Describe this image in detail. Capture all text, objects, and layout.",
        images=[image_b64]
    )
    # Direct invoke for the vision pass
    response = llm_vision.invoke([msg])
    return response.content

# --- 4. STREAMLIT UI ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Input")
    user_text = st.text_area("What should I do?", "Look at this image and save a summary to summary.txt")
    uploaded_file = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg"])
    
    run_btn = st.button("Run Agent", type="primary")

with col2:
    st.subheader("2. Agent Output")
    
    if run_btn:
        image_context = ""
        
        # Step A: If there is an image, convert it to text first
        if uploaded_file:
            with st.spinner("👀 Looking at image..."):
                try:
                    b64_img = get_image_base64(uploaded_file)
                    # Display thumbnail
                    st.image(uploaded_file, width=200)
                    
                    # Get description from Vision Model
                    description = analyze_image(b64_img)
                    image_context = f"\n\n[IMAGE CONTEXT]: The user uploaded an image. Here is what it contains: {description}"
                    st.success("Image analyzed!")
                    with st.expander("See what the AI saw"):
                        st.write(description)
                except Exception as e:
                    st.error(f"Error processing image: {e}")

        # Step B: Pass everything to the Agent
        if user_text:
            with st.spinner("🧠 Thinking & executing tools..."):
                # Combine User Query + Image Description
                full_prompt = f"User Request: {user_text} {image_context}"
                
                # Run the Agent
                response = agent_executor.invoke({"input": full_prompt})
                
                st.markdown("### Result:")
                st.write(response["output"])