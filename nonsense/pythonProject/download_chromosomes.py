import os
import shutil
import requests
import gzip


# Directory to save the file
directory = os.path.expanduser("~/../shared/chromosomes")
# Ensure the directory exists
os.makedirs(directory, exist_ok=True)


def download_chromosome(chromosome):
    url = f"https://ftp.ensembl.org/pub/release-112/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.chromosome.{chromosome}.fa.gz"
    # Filename
    filename = os.path.join(directory, f"Homo_sapiens.GRCh38.dna.chromosome.{chromosome}.fa.gz")
    fa = os.path.join(directory, f"Homo_sapiens.GRCh38.dna.chromosome.{chromosome}.fa")

    # Download the file
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    # Remove the response object
    del response
    print("File downloaded to:", filename)
    with gzip.open(filename, 'rb') as f_in:
        with open(fa, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    # Remove the gzipped file
    os.remove(filename)
    print("File unzipped")


for chromosome in range(2, 23):
    download_chromosome(chromosome)