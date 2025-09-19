import os
import requests
import time
import random
from bs4 import BeautifulSoup 
from urllib.parse import urljoin

URL = "https://edu-nc.gouv.cd/palmares_exetat2/"

def get_links():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()

        print("Status code:", response.status_code)
        html_page = response.content
        soup_page = BeautifulSoup(html_page, "html.parser")
        
        # Find card links
        links = soup_page.find_all("a", class_="views-list-image")
        
        # Fallback if no cards found
        if not links:
            links = soup_page.find_all("a", href=True)
            links = [link for link in links if "palmares" in link.get("href", "").lower()]
        
        print(f"Found {len(links)} links")
        return links
        
    except Exception as e:
        print(f"Error fetching main page: {e}")
        return [] 

def get_pub_links(links):
    pub_links = []
    for link in links:
        href = link.get("href")
        if href:
            full_url = urljoin(URL, href)
            pub_links.append(full_url)
            time.sleep(random.uniform(0.5, 1.5))
    return pub_links

def link_cat(pub_links):
    direct_pdfs = []
    html_pages = []

    for link in pub_links:
        if link.lower().endswith('.pdf'):
            direct_pdfs.append(link)
        else:
            html_pages.append(link)

    print(f"Found {len(direct_pdfs)} direct pdfs and {len(html_pages)} html pages")
    return direct_pdfs, html_pages

def get_pdf_name(pdf_link):
    name = pdf_link.split('/')[-1].replace('.pdf', '').replace('%20', ' ')

    return name
    
def get_pdfs(pub_links):
    #update the function to use key and value in a dictionnary 
    
    direct_pdfs_links, html_pages_links = link_cat(pub_links)
    
    for pdf_link in direct_pdfs_links:
        name = pdf_link.split('/')[-1].replace('.pdf', '').replace('%20', ' ')
        pdfs.append(pdf_link)
        pdf_names.append(name)
        print(f"direct pdf:{name}")
        
        except Exception as e:
            print(f" Error: {e}")
    
    return pdfs, pdf_names

def download_pdfs(pdfs, pdf_names):
    # Create download directory
    os.makedirs("downloads", exist_ok=True)
    
    success_count = 0
    
    for name, pdf_url in zip(pdf_names, pdfs):
        try:
            print(f"⬇ Downloading: {name}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Ensure PDF content
            if 'application/pdf' not in response.headers.get('content-type', ''):
                print(f"  Not a PDF: {pdf_url}")
                continue        
        except Exception as e:
            print(f" Error: {e}")
    
    return pdfs, pdf_names

def download_pdfs(pdfs, pdf_names):
    # Create download directory
    os.makedirs("downloads", exist_ok=True)
    
    success_count = 0
    
    for name, pdf_url in zip(pdf_names, pdfs):
        try:
            print(f"⬇ Downloading: {name}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Ensure PDF content
            if 'application/pdf' not in response.headers.get('content-type', ''):
                print(f"  Not a PDF: {pdf_url}")
                continue
            
            filename = f"downloads/{name}.pdf"
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            print(f" Downloaded: {filename}")
            success_count += 1
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f" Error downloading {name}: {e}")
    
    return success_count

def main():
    print(" Starting scraping...")
    
    # Step 1: Get card links
    links = get_links()
    if not links:
        print(" No links found. Exiting.")
        return
    
    # Step 2: Convert to full URLs
    print(" Getting publication links...")
    pub_links = get_pub_links(links)
    print(f" Found {len(pub_links)} total links")
    
    # Step 3: Extract PDF links
    print(" Extracting PDF links...")
    pdfs, pdf_names = get_pdfs(pub_links)
    
    if not pdfs:
        print(" No PDFs found. Exiting.")
        return
    
    print(f" Found {len(pdfs)} PDFs to download")
      
    # Step 4: Download PDFs
    print("⬇ Starting download process...")
    success_count = download_pdfs(pdfs, pdf_names)
    
    print(f" Completed! Downloaded {success_count}/{len(pdfs)} PDFs")

if __name__ == "__main__":
        main()
