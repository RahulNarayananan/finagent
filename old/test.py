from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
import streamlit as st
import os
#from dotenv import load_dotenv

prompt=ChatPromptTemplate.from_messages(
    [
        ("system","You are a financial tracking assistant and will receive inputs in format of texts, invoice pdfs, images your job is to extract the financial information such as spending classify it into broader categories such as entertainment, food, groceries and more, make up your own categories as necessary. In case of doubt ask follow up question to the user. "),
        ("user","{input}")
    ]
)

st.title('test run')
input_text=st.text_input("enter data")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption='Uploaded Image', use_column_width=True)

llm=Ollama(model="qwen3-vl:4b")
output_parser=StrOutputParser()
chain= prompt|llm|output_parser

if input_text:
    st.write(chain.invoke(input_text))