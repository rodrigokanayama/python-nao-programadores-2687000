import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pdfminer.high_level import extract_text

BASE_URL = "https://soc.ufpr.br/resolucoes-vigentes/"
PDF_DIR = "resolucoes"
OUTPUT_FILE = "resolucoes.txt"

os.makedirs(PDF_DIR, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("")

response = requests.get(BASE_URL, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.lower().endswith(".pdf"):
        links.append(urljoin(BASE_URL, href))
links = sorted(set(links))

print(f"Encontrados {len(links)} PDFs. Iniciando download e conversão...")

for url in links:
    pdf_name = os.path.join(PDF_DIR, os.path.basename(url))
    print(f"Processando {url}")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(pdf_name, "wb") as fp:
            fp.write(r.content)
    except Exception as e:
        print(f"Erro ao baixar {url}: {e}")
        continue
    try:
        text = extract_text(pdf_name)
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n----- {os.path.basename(url)} -----\n")
            f.write(text.strip() + "\n")
    except Exception as e:
        print(f"Erro ao converter {pdf_name}: {e}")

print("Concluído. Veja o conteúdo em", OUTPUT_FILE)
