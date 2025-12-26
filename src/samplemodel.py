"""
sample NLP program to test comparison of similarity scores
uses bible reference model to perform NLP comparison
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from bibleextraction import extractPassage, printPassage
from lyricsextraction import extractLyricsByFile, getFilesInDir, getSongname

# Initialise the NLP model
print("...initialising NLP model...\n")
MODEL_NAME = "odunola/sentence-transformers-bible-reference-final"
model = SentenceTransformer(MODEL_NAME)

# Data Loading
themes = ["Trust and Guidance", "Restoration and Peace", "Wrath and Judgment", "Jesus", 
          "Resurrection", "Love", "Faith", "Hope", "Power", "Joy", "Victory", "Creation", 
          "Suffering", "Grace", "Kingdom", "Sin", "Spirit", "Trinity", "Eternity", 
          "Humble", "Wisdom", "Mercy", "Heaven", "Throne"]
# bible_passage = extractPassage("Romans", 8, 31, 8, 39)
# song_lyric = extractLyricsByName("Your Word")

# Constants
DIRECT_THRESHOLD = 0.1  # Minimum "vibe" match to proceed to themes
THEME_RELEVANCE_THRESHOLD = 0.05    # Threshold to include a theme in results
THEME_VECS = model.encode(themes)
THEME_VECS = THEME_VECS / np.linalg.norm(THEME_VECS, axis=1, keepdims=True)


def chunk_text(text, max_tokens=400):
    """Splits long text into overlapping chunks to avoid model truncation."""
    words = text.split()
    return [" ".join(words[i : i + 400]) for i in range(0, len(words), 200)]

def get_normalized_vector(text, model):
    """Generates a document-level embedding (mean of chunks) and L2 normalizes it."""
    chunks = chunk_text(text)
    embeddings = model.encode(chunks)
    avg_vec = np.mean(embeddings, axis=0)
    return avg_vec / np.linalg.norm(avg_vec)

def get_thematic_signature(doc_vec, theme_vecs):
    """Applies ReLU filter and Normalization to create a 24-dimension fingerprint."""
    # Dot product with theme vectors
    raw_scores = np.dot(doc_vec, theme_vecs.T)
    # ReLU Filter: Set all negative or zero-signal themes to 0
    relu_scores = np.maximum(0, raw_scores)
    # L2 Normalize the signature so the sum of squares is 1
    norm = np.linalg.norm(relu_scores)
    return relu_scores / norm if norm > 0 else relu_scores


def matchScores(book, startChapter, startVerse, endChapter, endVerse):
    """
    Runs the NLP model to calculate similarity scores for each theme and return the results
    """
    bible_passage = extractPassage(book, startChapter, startVerse, endChapter, endVerse)
    passage_vec = get_normalized_vector(bible_passage, model)
    p_signature = get_thematic_signature(passage_vec, THEME_VECS)

    files = getFilesInDir()
    lyric_scores = {}
    for file in files:
        song_lyric = extractLyricsByFile(file)
        lyric_vec = get_normalized_vector(song_lyric, model)
        direct_similarity = np.dot(passage_vec, lyric_vec)

        # Decision Logic
        if direct_similarity < DIRECT_THRESHOLD:
            final_score = direct_similarity
            relevant_themes = []

        else:            
            # Thematic Analysis            
            l_signature = get_thematic_signature(lyric_vec, THEME_VECS)
            thematic_similarity = np.dot(p_signature, l_signature)

            # Finding relevant themes
            contributions = p_signature * l_signature
            relevant_themes = [
                themes[i] for i in range(len(themes)) 
                if contributions[i] > THEME_RELEVANCE_THRESHOLD
            ]
            
            # We weight Direct Similarity higher (60%) as it captures specific imagery/context
            final_score = (0.6 * direct_similarity) + (0.4 * thematic_similarity)
            
        lyric_scores[getSongname(file)] = {
            "score": f"{final_score:.4f}",
            "themes": relevant_themes,
        }
    
    return lyric_scores


def main():
    print("SelahSearch NLP Model: Get songs for your bible passage here!")
    book = input("Enter book: ")
    startChapter = int(input("Enter chapter to start from: "))
    startVerse = int(input("Enter verse to start from: "))
    endChapter = int(input("Enter chapter to end at: "))
    endVerse = int(input("Enter verse to end at: "))
    
    print(f"\nFinding songs that best relate theologically with {printPassage(book, startChapter, startVerse, endChapter, endVerse)}\n")
    results = matchScores(book, startChapter, startVerse, endChapter, endVerse)
    sorted_results = dict(sorted(results.items(), key=lambda item: float(item[1]['score']), reverse=True))
    
    print("\n--- RELATED SONGS (sorted by relevance) ---\n")
    for song, data in sorted_results.items():
        theme_str = ", ".join(data['themes']) if data['themes'] else ""
        print(f"{song}  (score {data['score']})")
        print(f" Key Themes: {theme_str}\n")
    print("--- ----------------------------------- ---\n\n")


if __name__ == "__main__":
    main()


# import numpy as np
# import tensorflow as tf
# from sentence_transformers import SentenceTransformer
# from bibleextraction import extractPassage
# from lyricsextraction import extractLyrics

# model_name = "odunola/sentence-transformers-bible-reference-final"
# model = SentenceTransformer(model_name)
# MAX_SEQ_LENGTH = model.max_seq_length  # Typically 512 for this model
# MAX_TOKENS = 420

# def chunk_text(text):
#     """Splits long text into overlapping chunks to avoid truncation."""
#     words = text.split()
#     # Simple word-based chunking as a proxy for tokens
#     return [" ".join(words[i : i + MAX_TOKENS]) for i in range(0, len(words), MAX_TOKENS // 2)]

# def get_aggregated_embedding(text, model):
#     """Encodes chunks of text and returns the mean embedding."""
#     chunks = chunk_text(text)
#     chunk_embeddings = model.encode(chunks)
#     # Average the embeddings of all chunks to represent the whole document
#     return np.mean(chunk_embeddings, axis=0)

# def create_normalized_signature(embedding, theme_vectors):
#     """
#     Applies ReLU filter and L2 Normalization to create a thematic profile.
#     """
#     # Calculate raw cosine similarity to themes
#     # (embedding is 1x768, theme_vectors is 24x768)
#     raw_scores = np.dot(embedding, theme_vectors.T) / (
#         np.linalg.norm(embedding) * np.linalg.norm(theme_vectors, axis=1)
#     )
    
#     # Apply ReLU: Keep only positive thematic signals (removes 'noise')
#     relu_scores = np.maximum(0, raw_scores)
    
#     # L2 Normalization: Scale the vector so the sum of squares equals 1
#     norm = np.linalg.norm(relu_scores)
#     if norm == 0:
#         return relu_scores
#     return relu_scores / norm

# # --- Execution ---

# # Extract Data
# bible_passage = extractPassage("Psalm", 119, 97, 119, 112)
# song_lyric = extractLyrics("Your Word")
# themes = ["Trust and Guidance", "Restoration and Peace", "Wrath and Judgment", "Jesus", 
#           "Resurrection", "Love", "Faith", "Hope", "Power", "Joy", "Victory", "Creation", 
#           "Suffering", "Grace", "Kingdom", "Sin", "Spirit", "Trinity", "Eternity", 
#           "Humble", "Wisdom", "Mercy", "Heaven", "Throne"]

# # Generate Document-Level Embeddings (Using Chunking)
# passage_vec = get_aggregated_embedding(bible_passage, model)
# lyric_vec = get_aggregated_embedding(song_lyric, model)
# theme_vecs = model.encode(themes)
# print(theme_vecs)

# # Generate Thematic Signatures (Profiles)
# passage_signature = create_normalized_signature(passage_vec, theme_vecs)
# lyric_signature = create_normalized_signature(lyric_vec, theme_vecs)

# # Calculate Final Selah Match Score (Cosine Similarity of the Signatures)
# selah_match_score = np.dot(passage_signature, lyric_signature)

# print(f"--- Thematic Match Results ---")
# print(f"Final Selah Match Score: {selah_match_score:.4f}")

# # Optional: Print Top 3 Themes for context
# top_passage = sorted(zip(themes, passage_signature), key=lambda x: x[1], reverse=True)[:3]
# print(f"Primary Passage Themes: {top_passage}")
