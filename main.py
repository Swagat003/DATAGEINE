import streamlit as st # type: ignore
import os
import uuid
import shutil
import time
from dotenv import load_dotenv
import google.generativeai as genai  # type: ignore
from bing_image_downloader import downloader  # type: ignore

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    st.error("GEMINI_API_KEY is not set in the environment variables.")
genai.configure(api_key=api_key)

DATASETS_DIR = 'datasets'
os.makedirs(DATASETS_DIR, exist_ok=True)

template = '''Given the dataset name and class name below, provide a refined search query that will result in specific, relevant images while avoiding unrelated content. If the generated query violates any policy, return only the given same class name.

Dataset Name: {dataset_name}
Class Name: {class_name}

The refined search query should:

1. Ensure the images match the intended category more specifically.
2. Exclude unrelated images such as logos, cartoons, emojis, illustrations, and objects not related to human subjects.
3. Include keywords like 'real person', 'authentic', 'natural', 'photo', 'realistic', 'single', etc. if appropriate.

For instance, if the dataset name is 'emotions' and the class name is 'sad', the refined query could be: 'sad person, facial expression, human emotion, realistic, real person -logo -cartoon -emoji -illustration -stock'.

Generate a refined search query for the given dataset and class name.
'''

model = genai.GenerativeModel("gemini-1.5-flash")



def process_download(dataset_name: str, classes: str, limit: int) -> bytes:
    """
    Downloads images for each class using a refined query generated via the generative AI,
    creates a zip archive of the downloaded images, cleans up temporary folders, and returns
    the zip file as bytes.
    """
    unique_id = str(uuid.uuid4())
    base_output_dir = os.path.join(DATASETS_DIR, unique_id)
    dataset_dir_name = dataset_name.replace(' ', '_')
    output_dir = os.path.join(base_output_dir, dataset_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    class_list = [cls.strip() for cls in classes.split(',') if cls.strip()]

    for cls in class_list:
        try:
            prompt = template.format(dataset_name=dataset_name, class_name=cls)
            response = model.generate_content(prompt)
            query = response.text.strip()
            if query.lower() == cls.lower():
                query = cls
            downloader.download(
                query,
                limit=limit,
                output_dir=output_dir,
                adult_filter_off=True,
                force_replace=False,
                timeout=60
            )
            old_dir = os.path.join(output_dir, query)
            new_dir = os.path.join(output_dir, cls)
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
        except Exception as e:
            try:
                downloader.download(
                    cls,
                    limit=limit,
                    output_dir=output_dir,
                    adult_filter_off=True,
                    force_replace=False,
                    timeout=60
                )
            except Exception as inner_e:
                shutil.rmtree(base_output_dir)
                raise Exception(f"Error downloading images for class '{cls}': {str(inner_e)}")
    
    try:
        zip_file_path = shutil.make_archive(output_dir, 'zip', output_dir)
    except Exception as e:
        shutil.rmtree(base_output_dir)
        raise Exception("Error creating zip archive: " + str(e))
    finally:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

    with open(zip_file_path, "rb") as f:
        zip_bytes = f.read()

    if os.path.exists(zip_file_path):
        os.remove(zip_file_path)
    if os.path.exists(base_output_dir):
        try:
            os.rmdir(base_output_dir)
        except Exception:
            pass

    return zip_bytes



st.set_page_config(page_title="Image Dataset Creator", layout="wide")
st.title("📸 Image Dataset Creator")
st.markdown(
    """
    Welcome! Use this app to generate a refined search query and download images based on your dataset requirements.
    
    **Instructions:**
    - Enter a dataset name (e.g. `animal_images`).
    - Enter one or more class names separated by commas (e.g. `dog, cat, horse`).
    - Specify how many images per class you want.
    - Click **Download Images** and wait while your dataset is being prepared.
    """
)

with st.form("dataset_form"):
    dataset_name = st.text_input("Dataset Name", placeholder="e.g., animal_images")
    classes = st.text_input("Classes (comma separated)", placeholder="e.g., dog, cat, horse")
    limit = st.number_input("Number of Images per Class", min_value=1, value=5, step=1)
    submitted = st.form_submit_button("Download Images")

if submitted:
    if not dataset_name or not classes:
        st.error("Please provide both the dataset name and the classes.")
    else:
        try:
            with st.spinner("Processing your request... This may take a while."):
                zip_data = process_download(dataset_name, classes, limit)
            st.success("Your dataset is ready!")
            st.download_button(
                label="⬇️ Download Zip File",
                data=zip_data,
                file_name=f"{dataset_name.replace(' ', '_')}.zip",
                mime="application/zip"
            )
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
