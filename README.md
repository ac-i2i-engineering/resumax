# ResuMax
[![Watch the video](https://img.youtube.com/vi/7lgOs64z_08/hqdefault.jpg)](https://www.youtube.com/watch?v=7lgOs64z_08)

## Overview

The ResuMax is a Django-based application that provides the API for creating and reviewing resumes. It leverages the RAG to analyze resume content and generate suggestions for improvement, ensuring that users can create professional and effective resumes with ease.

## Key Components

*   **Django:** The web framework used to build the backend.
*   **Django REST Framework:**  Used for building the API endpoints.
*   **Google Gemini API:**  The AI model used for resume analysis and content generation.
*   **Database:**  SQLite Stores user data, conversation history, and other application data.

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd resumax_backend
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv env
    source env/bin/activate  # On Linux/macOS
    env\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
