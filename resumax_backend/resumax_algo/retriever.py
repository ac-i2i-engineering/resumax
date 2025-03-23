from huggingface_hub import login
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, pipeline, BitsAndBytesConfig, AutoConfig
import torch
from textwrap import fill
from langchain.prompts import PromptTemplate
import locale
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

locale.getpreferredencoding = lambda: "UTF-8"

# from huggingface_hub import login
from django.conf import settings
# login(settings.HUGGINGFACE_API_KEY)
login("api_key")

import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    # Specify the directory where the FAISS index and metadata are saved
    save_directory = "vectordb"

    embedding_model_name = "sentence-transformers/all-mpnet-base-v2"
    # Check if CUDA is available
    if torch.cuda.is_available():
        model_kwargs = {"device": "cuda"}
    else:
        model_kwargs = {"device": "cpu"}
        print("CUDA not available, using CPU instead.")
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        model_kwargs=model_kwargs,
        multi_process=False,
    )

    # Load the FAISS index from the specified directory
    vector_store = FAISS.load_local(save_directory, embeddings,allow_dangerous_deserialization=True)

    # cell 6
    # Define the model
    model_name = "meta-llama/Llama-3.2-1B-Instruct"

    # Determine device and quantization configuration based on CUDA availability
    if torch.cuda.is_available():
        device = "cuda"
        quantization_config = BitsAndBytesConfig()
        model = AutoModelForCausalLM.from_pretrained(model_name,
                                                 device_map=device,
                                                 quantization_config=quantization_config,
                                                 trust_remote_code=True)
    else:
        device = "cpu"
        # Remove quantization_config and use cpu
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
        )  # Move the model to the device

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)

    gen_cfg = GenerationConfig.from_pretrained(model_name)
    gen_cfg.max_new_tokens = 512
    gen_cfg.temperature = 0.0000001
    gen_cfg.return_full_text = True
    gen_cfg.do_sample = True
    gen_cfg.repetition_penalty = 1.11

    pipe = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        generation_config=gen_cfg,
        device=device # Ensure pipeline uses the correct device
    )

    llm = HuggingFacePipeline(pipeline=pipe)

    # cell 7
    # Define the prompt template
    prompt_template_llama3 = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are a resume reviewer. You will be given a resume. Use the following context to answer the question and give tailored feedback
    on how to improve the resume. Be concise and to the point. Return in this format:

    <general review of the resume>
    [The text of the general review]
    </general review of the resume>

    <tailored feedback answering the question>
    [The text of the tailored feedback]
    </tailored feedback>

    <Next steps for improvement>
    [The text of the next steps for improvement]
    </Next steps for improvement>

    {context}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

    prompt = PromptTemplate(template=prompt_template_llama3, input_variables=["context", "question"])

    # cell 8
    # Define the retrieval QA chain
    Chain_pdf = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_type="similarity_score_threshold", search_kwargs={'k': 10, 'score_threshold': 0.2}),
        chain_type_kwargs={"prompt": prompt},
    )

    query = """just in direct words, out of 100%, how good is this. you explain why?

    Work Experience:
    Software Engineering Intern | Google | Summer 2024
    - Developed and optimized backend services for a large-scale distributed system, improving performance by 20%.
    - Led a team of three interns in implementing a feature that reduced data retrieval time by 30%.

    Teaching Assistant | Amherst College | Fall 2023 - Present
    - Led weekly discussions and mentored students in algorithms and data structures.
    - Created practice problems that improved students’ understanding of computational complexity.
    """
    result = Chain_pdf.invoke(query)
    # Strip out any template artifacts from the result
    clean_result = result['result'].split("<|eot_id|><|start_header_id|>assistant<|end_header_id|>")[-1].strip()
    print(fill(clean_result, width=200))