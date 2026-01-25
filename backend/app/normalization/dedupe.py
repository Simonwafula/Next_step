from datasketch import MinHash, MinHashLSH
from rapidfuzz import fuzz
import re

def get_shingles(text: str, k=5):
    """Generate k-shingles from text."""
    if not text:
        return set()
    text = re.sub(r"\s+", " ", text.lower().strip())
    return set(text[i:i+k] for i in range(len(text) - k + 1))

def create_minhash(text: str, num_perm=128):
    """Create a MinHash object from text shingles."""
    shingles = get_shingles(text)
    m = MinHash(num_perm=num_perm)
    for s in shingles:
        m.update(s.encode('utf8'))
    return m

class Deduplicator:
    def __init__(self, threshold=0.8, num_perm=128):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self.id_map = {} # job_id -> minhash
        
    def add_job(self, job_id, text):
        m = create_minhash(text)
        self.lsh.insert(str(job_id), m)
        self.id_map[job_id] = m
        
    def find_duplicates(self, job_id, text):
        """Find potential duplicates in the LSH index."""
        m = create_minhash(text)
        candidates = self.lsh.query(m)
        
        duplicates = []
        for cand_id in candidates:
            if cand_id == str(job_id):
                continue
                
            # Fuzzy validation
            # In a real scenario we'd fetch the candidate text
            # but for this module we assume it's external or pre-computed
            duplicates.append({
                "job_id": int(cand_id),
                "score": self.id_map[int(cand_id)].jaccard(m)
            })
            
        return sorted(duplicates, key=lambda x: x["score"], reverse=True)

def is_near_duplicate(text1: str, text2: str, threshold=0.9) -> bool:
    """Fuzzy string comparison for two job descriptions."""
    if not text1 or not text2:
        return False
    # Use token sort ratio for robustness against word ordering
    score = fuzz.token_sort_ratio(text1, text2) / 100.0
    return score >= threshold
