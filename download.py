import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(
    description='Download HTML content and images from a Flask page.')
parser.add_argument(
    'name', type=str, help='The name to be used in the URL and file names')
args = parser.parse_args()

# URL of the Flask route
url = f'http://127.0.0.1:5000/{args.name}'

# Make a GET request to the URL
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Create a directory to save images
    os.makedirs('images', exist_ok=True)

    # Find all image tags
    img_tags = soup.find_all('img')

    for img in img_tags:
        img_url = img['src']
        # Handle relative URLs
        img_url = urljoin(url, img_url)
        img_name = os.path.basename(img_url)
        img_path = os.path.join('images', img_name)

        # Download the image
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            with open(img_path, 'wb') as img_file:
                img_file.write(img_response.content)
            # Update the image source in the HTML to the local path
            img['src'] = img_path

    # Write the modified HTML content to a file
    with open("download_files/"f'{args.name}.html', 'w', encoding='utf-8') as file:
        file.write(str(soup))

    print(
        f"Content and images have been written to {args.name}.html and images/ directory")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
