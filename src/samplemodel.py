# sample NLP program to test comparison of similarity scores
# uses bible reference model to perform NLP comparison
import numpy as np
import tensorflow as tf
from sentence_transformers import SentenceTransformer
from bibleextraction import extractPassage
from lyricsextraction import extractLyrics

model_name = "odunola/sentence-transformers-bible-reference-final"
model = SentenceTransformer(model_name)
MAX_SEQ_LENGTH = model.max_seq_length  # Typically 512 for this model
MAX_TOKENS = 420

def chunk_text(text):
    """Splits long text into overlapping chunks to avoid truncation."""
    words = text.split()
    # Simple word-based chunking as a proxy for tokens
    return [" ".join(words[i : i + MAX_TOKENS]) for i in range(0, len(words), MAX_TOKENS // 2)]

def get_aggregated_embedding(text, model):
    """Encodes chunks of text and returns the mean embedding."""
    chunks = chunk_text(text)
    chunk_embeddings = model.encode(chunks)
    # Average the embeddings of all chunks to represent the whole document
    return np.mean(chunk_embeddings, axis=0)

def create_normalized_signature(embedding, theme_vectors):
    """
    Applies ReLU filter and L2 Normalization to create a thematic profile.
    """
    # Calculate raw cosine similarity to themes
    # (embedding is 1x768, theme_vectors is 24x768)
    raw_scores = np.dot(embedding, theme_vectors.T) / (
        np.linalg.norm(embedding) * np.linalg.norm(theme_vectors, axis=1)
    )
    
    # Apply ReLU: Keep only positive thematic signals (removes 'noise')
    relu_scores = np.maximum(0, raw_scores)
    
    # L2 Normalization: Scale the vector so the sum of squares equals 1
    norm = np.linalg.norm(relu_scores)
    if norm == 0:
        return relu_scores
    return relu_scores / norm

# --- Execution ---

# Extract Data
bible_passage = extractPassage("Psalm", 119, 97, 119, 112)
song_lyric = extractLyrics("Your Word")
themes = ["Trust and Guidance", "Restoration and Peace", "Wrath and Judgment", "Jesus", 
          "Resurrection", "Love", "Faith", "Hope", "Power", "Joy", "Victory", "Creation", 
          "Suffering", "Grace", "Kingdom", "Sin", "Spirit", "Trinity", "Eternity", 
          "Humble", "Wisdom", "Mercy", "Heaven", "Throne"]

# Generate Document-Level Embeddings (Using Chunking)
passage_vec = get_aggregated_embedding(bible_passage, model)
lyric_vec = get_aggregated_embedding(song_lyric, model)
theme_vecs = model.encode(themes)
print(theme_vecs)

# Generate Thematic Signatures (Profiles)
passage_signature = create_normalized_signature(passage_vec, theme_vecs)
lyric_signature = create_normalized_signature(lyric_vec, theme_vecs)

# Calculate Final Selah Match Score (Cosine Similarity of the Signatures)
selah_match_score = np.dot(passage_signature, lyric_signature)

print(f"--- Thematic Match Results ---")
print(f"Final Selah Match Score: {selah_match_score:.4f}")

# Optional: Print Top 3 Themes for context
top_passage = sorted(zip(themes, passage_signature), key=lambda x: x[1], reverse=True)[:3]
print(f"Primary Passage Themes: {top_passage}")



# # sample data, replace with calls to database
# # bible_passage = "The Lord is my shepherd; I shall not want."
# # song_lyric = "He leads me beside the still waters, He restores my soul."
# bible_passage = extractPassage("Genesis", 1, 1, 1, 31)
# song_lyric = extractLyrics("Your Word")

# themes = [
#     "Trust and Guidance",
#     "Restoration and Peace",
#     "Wrath and Judgment",
#     "Jesus",
#     "Resurrection",
#     "Love",
#     "Faith",
#     "Hope",
#     "Power",
#     "Joy",
#     "Victory",
#     "Creation",
#     "Suffering",
#     "Grace",
#     "Kingdom",
#     "Sin",
#     "Spirit",
#     "Trinity",
#     "Eternity",
#     "Humble",
#     "Wisdom",
#     "Mercy",
#     "Heaven",
#     "Throne",
# ]

# # Generate Embeddings (Vectors)
# # model.encode converts the text into the vector representation (e.g., a 384-dimension vector)
# passage_vec = model.encode([bible_passage], convert_to_tensor=False)
# lyric_vec = model.encode([song_lyric], convert_to_tensor=False)
# theme_vecs = model.encode(themes, convert_to_tensor=False)

# # Convert all to TensorFlow Tensors for similarity calculation
# passage_tensor = tf.convert_to_tensor(passage_vec, dtype=tf.float32)
# lyric_tensor = tf.convert_to_tensor(lyric_vec, dtype=tf.float32)
# theme_tensors = tf.convert_to_tensor(theme_vecs, dtype=tf.float32)

# print(f"Passage Vector Shape: {passage_tensor.shape}")
# print(f"Theme Vectors Shape: {theme_tensors.shape}")


# def calculate_semantic_similarity(query_tensor, candidate_tensors):
#     """
#     Calculate Cosine Similarity between query and set of candidates
#     - Normalize vectors (L2-normalization)
#     - Calculate dot product
    
#     Returns:
#     - Tensor of similarity scores
#     """
#     query_norm = tf.nn.l2_normalize(query_tensor, axis=1)
#     candidates_norm = tf.nn.l2_normalize(candidate_tensors, axis=1)
    
#     similarities = tf.matmul(query_norm, candidates_norm, transpose_b=True)
#     return similarities[0].numpy()


# # Match the Bible Passage to Themes
# passage_scores = calculate_semantic_similarity(passage_tensor, theme_tensors)
# ranked_passage_matches = sorted(zip(themes, passage_scores), key=lambda x: x[1], reverse=True)

# # Match the Song Lyric to Themes
# lyric_scores = calculate_semantic_similarity(lyric_tensor, theme_tensors)
# ranked_lyric_matches = sorted(zip(themes, lyric_scores), key=lambda x: x[1], reverse=True)

# print("\n--- Bible Passage Theme Matching ---")
# for theme, score in ranked_passage_matches:
#     print(f"Theme: '{theme}' | Score: {score:.4f}")

# print("\n--- Song Lyric Theme Matching ---")
# for theme, score in ranked_lyric_matches:
#     print(f"Theme: '{theme}' | Score: {score:.4f}")

