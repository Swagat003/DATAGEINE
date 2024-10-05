from flask import Flask, request, jsonify
from bing_image_downloader import downloader  # type: ignore
import os
import shutil

app = Flask(__name__)

@app.route('/download_images', methods=['GET'])
def download_images():
    dataset_name = request.args.get('dataset_name')
    classes = request.args.get('classes')  
    limit = request.args.get('limit', default=5, type=int)

    if not dataset_name or not classes:
        return jsonify({'error': 'Dataset name and classes are required.'}), 400

    output_dir = os.path.join('datasets', dataset_name)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir)

    class_list = [cls.strip() for cls in classes.split(',')]

    for cls in class_list:
        try:
            downloader.download(cls, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
        except Exception as e:
            return jsonify({'error': f'Error downloading images for class "{cls}": {str(e)}'}), 500

    return jsonify({'message': f'Downloaded images for classes: {class_list} in dataset "{dataset_name}".'}), 200

if __name__ == '__main__':
    app.run(debug=True)

# Example Test URL: 
# http://127.0.0.1:5000/download_images?dataset_name=animal_images&classes=dog,cat,horse&limit=10
