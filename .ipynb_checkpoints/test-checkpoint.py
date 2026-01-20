{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 4,
   "id": "cf0ff744-e9e1-4eaa-ba7f-2d8c1f8370cd",
   "metadata": {},
   "outputs": [],
   "source": [
    "from langchain_openai import ChatOpenAI\n",
    "from langchain_core.prompts import ChatPromptTemplate\n",
    "from langchain_core.output_parsers import StrOutputParser\n",
    "from langchain_community.llms import Ollama\n",
    "import streamlit as st\n",
    "import os\n",
    "from dotenv import load_dotenv"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "id": "82aaa241-d72e-4c81-a20b-c326294b7328",
   "metadata": {},
   "outputs": [],
   "source": [
    "prompt=ChatPromptTemplate.from_messages(\n",
    "    [\n",
    "        (\"system\",\"You are a financial tracking assistant and will receive inputs in format of texts, invoice pdfs, images your job is to extract the financial information such as spending classify it into broader categories such as entertainment, food, groceries and more, make up your own categories as necessary. In case of doubt ask follow up question to the user. \"),\n",
    "        (\"user\",\"{input}\")\n",
    "    ]\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 8,
   "id": "b6f26887-7ed6-40da-bfba-e5275ee8ff40",
   "metadata": {},
   "outputs": [
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "2025-12-23 11:39:57.863 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.864 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.864 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.865 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.865 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.866 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.866 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.866 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.866 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.867 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.867 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.867 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.869 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.869 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.869 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n",
      "2025-12-23 11:39:57.869 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.\n"
     ]
    }
   ],
   "source": [
    "st.title('test run')\n",
    "input_text=st.text_input(\"enter data\")\n",
    "\n",
    "uploaded_file = st.file_uploader(\"Choose an image...\", type=[\"jpg\", \"jpeg\", \"png\"])\n",
    "\n",
    "if uploaded_file is not None:\n",
    "    # Display the uploaded image\n",
    "    image = Image.open(uploaded_file)\n",
    "    st.image(image, caption='Uploaded Image', use_column_width=True)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 10,
   "id": "257c5fcf-ce43-4087-973c-e5b36aba2060",
   "metadata": {},
   "outputs": [],
   "source": [
    " llm=Ollama(model=\"qwen3-vl:4b\")\n",
    "output_parser=StrOutputParser()\n",
    "chain= prompt|llm|output_parser"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 11,
   "id": "65ccd006-18da-471a-81fe-f8bd30c577b7",
   "metadata": {},
   "outputs": [],
   "source": [
    "if input_text:\n",
    "    st.write(chain.invoke(input_text))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "523db892-fadf-4a88-8d5d-3057fe21112c",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
