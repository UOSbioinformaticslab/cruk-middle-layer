import os


def get_chromosomes():
    """returns a dictionary with a string for each chromosome. Unidentified nucleotides are
    marked as N."""
    directory = "/home/shared/chromosomes"
    chromosomes = {}
    for chromosome in range(1,23):
        fa = os.path.join(directory, f"Homo_sapiens.GRCh38.dna.chromosome.{chromosome}.fa")
        with open(fa) as f:
            chromosomes[chromosome] = ''.join(f.read().split('\n')[1:])
    return chromosomes

chromosomes = get_chromosomes()
