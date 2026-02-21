import requests
from bs4 import BeautifulSoup

def get_python_314_features():
    try:
        url = "https://www.python.org/downloads/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        version_tags = soup.find_all('h2')
        for tag in version_tags:
            if 'Python 3.14' in tag.text:
                return "Python 3.14 is available"
    except Exception as e:
        return f"Error: {str(e)}"

    return "Python 3.14 is not yet officially released"

def main():
    print(get_python_314_features())

if __name__ == "__main__":
    main()