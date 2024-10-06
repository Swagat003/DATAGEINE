from flask import Flask, request, jsonify, send_from_directory
from bing_image_downloader import downloader  # type: ignore
import os
from dotenv import load_dotenv
import shutil
import uuid
from apscheduler.schedulers.background import BackgroundScheduler # type: ignore
import time
import google.generativeai as genai # type: ignore


app = Flask(__name__)

DATASETS_DIR = 'datasets'

os.makedirs(DATASETS_DIR, exist_ok=True)

folder_expiry_times = {}

scheduler = BackgroundScheduler()

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=api_key)

template = '''Given the dataset name and class name below, provide a refined search query that will result in specific, relevant images while avoiding unrelated content. If the generated query violates any policy, return only the given same class name.

Dataset Name: {dataset_name}
Class Name: {class_name}

The refined search query should:

1. Ensure the images match the intended category more specifically.
2. Exclude unrelated images such as logos, cartoons, emojis, illustrations, and objects not related to human subjects.
3. Include keywords like 'real person', 'authentic', 'natural', 'photo', 'realistic', etc. if appropriate.

For instance, if the dataset name is 'emotions' and the class name is 'sad', the refined query could be: 'sad person, facial expression, human emotion, realistic, real person -logo -cartoon -emoji -illustration -stock'.

Generate a refined search query for the given dataset and class name.
'''
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/download_images', methods=['GET'])
def download_images():
    dataset_name = request.args.get('dataset_name')
    classes = request.args.get('classes')
    limit = request.args.get('limit', default=5, type=int)

    if not dataset_name or not classes:
        return jsonify({'error': 'Dataset name and classes are required.'}), 400

    unique_id = str(uuid.uuid4())
    base_output_dir = os.path.join(DATASETS_DIR, unique_id)
    output_dir = os.path.join(base_output_dir, dataset_name)

    os.makedirs(output_dir)

    class_list = [cls.strip() for cls in classes.split(',')]

    for cls in class_list:
        try:
            response = model.generate_content(template.format(dataset_name=dataset_name, class_name=cls))
            query = response.text.strip()
            if query.lower() == cls.lower():  
                query = cls  
            downloader.download(query, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
            old_dir = os.path.join(output_dir, query)
            new_dir = os.path.join(output_dir, cls)
            os.rename(old_dir, new_dir)

        except Exception as e:
            try:
                downloader.download(cls, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
            except Exception as e:
                shutil.rmtree(base_output_dir)
                return jsonify({'error': f'Error downloading images for class "{cls}": {str(e)}'}), 500

    zip_file_path = shutil.make_archive(output_dir, 'zip', output_dir)
    shutil.rmtree(output_dir)

    folder_expiry_times[unique_id] = time.time() + 60

    zip_file_name = os.path.basename(zip_file_path)

    return jsonify({
        'message': f'Downloaded image dataset "{dataset_name}" for classes: {class_list} in 60 sec.',
        'path': f'/download_zip/{unique_id}/{zip_file_name}',
        'download_link': f'http://127.0.0.1:5000/download_zip/{unique_id}/{zip_file_name}'
    }), 200


@app.route('/download_zip/<unique_id>/<path:filename>', methods=['GET'])
def download_zip(unique_id, filename):
    directory = os.path.join(app.root_path, DATASETS_DIR, unique_id)
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'The requested zip file has been removed from the server.'}), 404

    return send_from_directory(directory=directory, path=filename, as_attachment=True)

def delete_expired_folders():
    """Delete folders that have passed their expiry time."""
    current_time = time.time()
    for unique_id, expiry_time in list(folder_expiry_times.items()):
        if current_time > expiry_time:
            folder_path = os.path.join(DATASETS_DIR, unique_id)
            try:
                shutil.rmtree(folder_path)
                del folder_expiry_times[unique_id]
                print(f"Deleted expired folder: {folder_path}")
            except Exception as e:
                print(f"Error deleting folder: {str(e)}")

scheduler.add_job(delete_expired_folders, 'interval', seconds=30)
scheduler.start()

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        scheduler.shutdown()


# Example Test URL: 
# http://127.0.0.1:5000/download_images?dataset_name=animal_images&classes=dog,cat,horse&limit=10
# http://192.168.29.169:5000/download_images?dataset_name=animal_images&classes=dog,cat,horse&limit=5