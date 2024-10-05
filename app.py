from flask import Flask, request, jsonify, send_from_directory
from bing_image_downloader import downloader  # type: ignore
import os
import shutil
import threading
import time
import uuid

app = Flask(__name__)

@app.route('/download_images', methods=['GET'])
def download_images():
    dataset_name = request.args.get('dataset_name')
    classes = request.args.get('classes') 
    limit = request.args.get('limit', default=5, type=int)

    if not dataset_name or not classes:
        return jsonify({'error': 'Dataset name and classes are required.'}), 400

    unique_id = str(uuid.uuid4())
    base_output_dir = os.path.join('datasets', unique_id)
    output_dir = os.path.join(base_output_dir, dataset_name)

    os.makedirs(output_dir)

    class_list = [cls.strip() for cls in classes.split(',')]

    for cls in class_list:
        try:
            downloader.download(cls, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
        except Exception as e:
            return jsonify({'error': f'Error downloading images for class "{cls}": {str(e)}'}), 500

    zip_file_path = shutil.make_archive(output_dir, 'zip', output_dir)
    shutil.rmtree(output_dir)
    
    threading.Thread(target=delete_folder_after_delay, args=(base_output_dir, 60)).start()

    zip_file_name = os.path.basename(zip_file_path)

    return jsonify({'message': f'Downloaded image dataset "{dataset_name}" for classes: {class_list} in 60 sec.', 'path': f'/download_zip/{unique_id}/{zip_file_name}', 'download_link': f'http://127.0.0.1:5000/download_zip/{unique_id}/{zip_file_name}'}), 200

@app.route('/download_zip/<unique_id>/<path:filename>', methods=['GET'])
def download_zip(unique_id, filename):
    directory = os.path.join(app.root_path, 'datasets', unique_id)
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'The requested zip file has been removed from the server.'}), 404

    return send_from_directory(directory=directory, path=filename, as_attachment=True)

def delete_folder_after_delay(folder_path, delay):
    """Delete the folder after a specified delay."""
    time.sleep(delay)
    try:
        shutil.rmtree(folder_path)
        print(f"Deleted folder: {folder_path}")
    except Exception as e:
        print(f"Error deleting folder: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)

# Example Test URL: 
# http://127.0.0.1:5000/download_images?dataset_name=animal_images&classes=dog,cat,horse&limit=10