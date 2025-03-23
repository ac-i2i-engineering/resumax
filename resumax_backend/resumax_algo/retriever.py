from huggingface_hub import login
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, pipeline, BitsAndBytesConfig, AutoConfig
import torch
from textwrap import fill
from langchain.prompts import PromptTemplate
import locale
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import HuggingFaceEmbeddings #Deprecated
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

locale.getpreferredencoding = lambda: "UTF-8"

# from huggingface_hub import login
from django.conf import settings
# login(settings.HUGGINGFACE_API_KEY)
login("API_KEY")

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
# Import the process_loader function from the new file
from pdf_processing import process_loader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the pdfs directory
pdfs_dir = os.path.join(current_dir, 'pdfs')

# Get all .pdf files in the pdfs/ directory and subdirectories
pdf_files = []
for root, dirs, files in os.walk(pdfs_dir):
    for file in files:
        if file.endswith('.pdf'):
            pdf_files.append(os.path.join(root, file))

# Create loaders for each .pdf file
loaders = [PyMuPDFLoader(fn) for fn in pdf_files]

chunked_pdf_doc = []
# print("Loading documents")
def process_pdf(loader):
    try:
        return process_loader(loader)
    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        return []  # Return an empty list in case of an error

if __name__ == '__main__':
    # Wrap the main execution block in the `if __name__ == '__main__':` guard
    with ProcessPoolExecutor(max_workers=10) as executor:  # Reduce workers to avoid memory issues
        futures = [executor.submit(process_pdf, loader) for loader in loaders]
        for future in as_completed(futures):
            logging.info(f"Process {future} completed")
            chunked_pdf_doc.extend(future.result())
    # print(len(chunked_pdf_doc))
    
    embedding_model_name = "sentence-transformers/all-mpnet-base-v2"
    # Check if CUDA is available
    if torch.cuda.is_available():
        model_kwargs = {"device": "cuda"}
    else:
        model_kwargs = {"device": "cpu"}
        # print("CUDA not available, using CPU instead.")
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        model_kwargs=model_kwargs,
        multi_process=False, # set to false to avoid the RuntimeError
    )

    vector_store = FAISS.from_documents(chunked_pdf_doc, embeddings)

    # Specify the directory where you want to save the FAISS index and metadata
    save_directory = "faiss_index"

    # Save the FAISS index and metadata to the specified directory
    vector_store.save_local(save_directory)

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

    prompt_template=prompt_template_llama3

    prompt = PromptTemplate(
        input_variables=["text"],
        template=prompt_template,
    )
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    # cell 8
    # Define the retrieval QA chain
    Chain_pdf = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_type="similarity_score_threshold", search_kwargs={'k': 10, 'score_threshold': 0.2}),
        chain_type_kwargs={"prompt": prompt},
    )

    query = """Does the resume highlight leadership experience effectively?

    Work Experience:
    Software Engineering Intern | Google | Summer 2024
    - Developed and optimized backend services for a large-scale distributed system, improving performance by 20%.
    - Led a team of three interns in implementing a feature that reduced data retrieval time by 30%.

    Teaching Assistant | Amherst College | Fall 2023 - Present
    - Led weekly discussions and mentored students in algorithms and data structures.
    - Created practice problems that improved students’ understanding of computational complexity.
    """
    result = Chain_pdf.invoke(query)
    print(fill(result['result'].strip(), width=200))
    print("##########################################################################")

    query = """Are the technical skills presented in a way that aligns with industry expectations?

    Work Experience:
    Software Engineer | Startup XYZ | 2023 - Present
    - Built RESTful APIs using Django, handling over 100k requests daily.
    - Developed a CI/CD pipeline that reduced deployment time by 50%.

    Research Assistant | AI Lab | 2022 - 2023
    - Implemented neural network verification techniques in Python.
    - Optimized matrix computations, reducing runtime by 40%.
    """
    result = Chain_pdf.invoke(query)
    print(fill(result['result'].strip(), width=200))