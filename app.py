from flask import Flask, request, jsonify
from bing_image_downloader import downloader # type: ignore
import os

app = Flask(__name__)

@app.route('/download_images', methods=['GET'])
def download_images():
    query = request.args.get('query')
    limit = request.args.get('limit', default=5, type=int)  
    output_dir = 'datasets'  
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        downloader.download(query, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
        return jsonify({'message': f'Downloaded {limit} images for query "{query}".'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

# http://127.0.0.1:5000/download_images?query=dog&limit=10