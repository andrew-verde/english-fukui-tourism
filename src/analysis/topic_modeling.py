"""
Topic Modeling Module

Performs topic extraction using LDA and other methods to identify
key themes in Fukui tourism discussions.
"""

import logging
import re
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import warnings

# gensim imported lazily inside fit_gensim() to avoid blocking assign_primary_theme()

from ..utils.logger import setup_logger

logger = setup_logger(__name__)
warnings.filterwarnings('ignore')

# 5-category taxonomy required by statistical_requirements.md (SR-01).
# Priority order determines which theme wins when multiple keywords match.
#
# Keyword hygiene rules (audit 2026-05-19):
#   - Scenic: bare "beautiful" removed; replaced with compound scenic phrases only.
#     Bare "beautiful" misclassified temple/castle reviews as Scenic (46% of prior
#     Scenic classifications matched "beautiful" alone with no other scenic keyword).
#   - Cultural (formerly "Emotional"): renamed to better reflect keyword scope,
#     which covers Zen/spiritual AND broader cultural/heritage content.
#     "historic", "heritage", "traditional", "culture", "cultural" retained —
#     these are genuinely cultural signals; theme label updated to match.
#   - Logistics: "crowded", "crowd", "queue", "wait", "expensive" removed.
#     These keywords overlap with waiting_crowding and price_value friction codes,
#     making any Theme × Friction cross-tabulation partially circular. Logistics
#     now covers transport/access/navigation only.
_THEME_KEYWORDS: Dict[str, List[str]] = {
    "Dinosaur": [
        # Keep Dinosaur-specific signals only. Do NOT include generic museum terms
        # like "museum", "exhibit", or "exhibition" (these apply to many cities
        # and will misclassify non-dinosaur museums as Dinosaur).
        "dinosaur", "dinosaurs", "fossil", "fossils", "fukuiraptor",
        "paleontology", "palaeontology", "bone", "bones",
        "dinosaur museum",
    ],
    "Food": [
        # Note: "eat" and "dish" are retained despite being somewhat generic.
        # False-positive risk documented in output/statistical_test_explanations.md.
        "food", "foods", "crab", "soba", "restaurant", "cuisine", "eating",
        "eat", "dish", "taste", "menu", "sake", "izakaya", "seafood",
        "ramen", "noodle", "fish", "delicious", "meal", "lunch", "dinner",
    ],
    "Scenic": [
        # "beautiful" removed: too generic, fired on temples/castles (46% of prior
        # Scenic hits). Replaced with compound scenic-specific phrases.
        "view", "views", "scenery", "scenic", "landscape", "coastal", "coast",
        "cliff", "cliffs", "tojinbo", "sea", "ocean", "beach", "waterfall",
        "mountain", "nature", "gorge", "canyon", "lake",
        "beautiful scenery", "beautiful view", "beautiful landscape",
        "beautiful coast", "beautiful nature", "beautiful scenery",
    ],
    "Cultural": [
        # Renamed from "Emotional". Keywords cover Zen/spiritual AND broader
        # cultural/heritage content — "Cultural" is a more accurate label.
        "zen", "temple", "eiheiji", "spiritual", "peaceful", "meditation",
        "buddhist", "buddhism", "heritage", "traditional", "historic",
        "shrine", "culture", "cultural", "prayer", "sacred", "serene",
    ],
    "Logistics": [
        # "crowded", "crowd", "queue", "wait", "expensive" removed to eliminate
        # overlap with waiting_crowding and price_value friction codes.
        # Logistics now covers transport/access/navigation only.
        "transport", "transportation", "train", "bus", "car", "rental",
        "access", "difficult", "far", "remote", "shinkansen",
        "parking", "taxi", "drive", "direction", "inconvenient", "limited",
    ],
}

_THEME_PRIORITY = ["Dinosaur", "Food", "Scenic", "Cultural", "Logistics"]


def assign_primary_theme(text: str) -> Optional[str]:
    """
    Assign single primary theme using keyword priority (SR-01).
    Priority: Dinosaur > Food > Scenic > Cultural > Logistics.
    Word-boundary matching prevents partial matches (e.g. 'view' inside 'review').
    Returns None if no keywords match (excluded from chi-square analysis).
    """
    if not isinstance(text, str) or not text.strip():
        return None
    text_lower = text.lower()
    for theme in _THEME_PRIORITY:
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower)
               for kw in _THEME_KEYWORDS[theme]):
            return theme
    return None


def assign_primary_theme_with_keyword(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Like assign_primary_theme(), but also returns the first matched keyword.
    Useful for diagnostics/auditing of theme assignment.
    """
    if not isinstance(text, str) or not text.strip():
        return None, None
    text_lower = text.lower()
    for theme in _THEME_PRIORITY:
        for kw in _THEME_KEYWORDS[theme]:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return theme, kw
    return None, None


class TopicModel:
    """Extract and analyze topics from text data."""
    
    def __init__(self, num_topics: int = 5, method: str = 'lda', testing_mode: Optional[bool] = None):
        """
        Initialize topic model.
        
        Args:
            num_topics: Number of topics to extract
            method: 'lda' (Latent Dirichlet Allocation) or 'nmf'
            testing_mode: Limit processing for testing (optional, uses TESTING_MODE env var if not provided)
        """
        import os
        self.testing_mode = testing_mode if testing_mode is not None else os.getenv('TESTING_MODE', 'false').lower() == 'true'
        self.num_topics = num_topics if not self.testing_mode else min(num_topics, 3)  # Reduce topics in testing
        self.method = method
        self.model = None
        self.vectorizer = None
        self.topics = None
        
        logger.info(f"Topic model initialized (topics: {self.num_topics}, testing_mode: {self.testing_mode})")
        
    def prepare_documents(self, texts: List[str]) -> Tuple:
        """
        Prepare documents for topic modeling.
        
        Args:
            texts: List of text documents
            
        Returns:
            Tuple of (doc_term_matrix, feature_names, vectorizer)
        """
        logger.info(f"Preparing {len(texts)} documents for topic modeling...")
        
        # Remove empty texts
        texts = [t for t in texts if isinstance(t, str) and len(t) > 0]
        
        # Create document-term matrix
        vectorizer = CountVectorizer(
            max_df=0.95,  # Remove words that appear in >95% of documents
            min_df=2,     # Remove words that appear in <2 documents
            stop_words='english',
            max_features=1000
        )
        
        doc_term_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        logger.info(f"Created document-term matrix: {doc_term_matrix.shape}")
        
        return doc_term_matrix, feature_names, vectorizer
    
    def fit_lda(
        self,
        doc_term_matrix,
        feature_names,
        max_iter: int = 10,
        random_state: int = 42
    ):
        """Fit LDA topic model."""
        logger.info(f"Fitting LDA model with {self.num_topics} topics...")
        
        self.model = LatentDirichletAllocation(
            n_components=self.num_topics,
            max_iter=max_iter,
            random_state=random_state,
            verbose=0
        )
        
        self.model.fit(doc_term_matrix)
        self.vectorizer = feature_names
        
        logger.info("LDA model fitted successfully")
        self._extract_topics(doc_term_matrix)
    
    def fit_gensim(self, texts: List[str], passes: int = 10):
        """Fit Gensim LDA model."""
        from gensim import corpora, models  # noqa: PLC0415 — lazy import
        logger.info(f"Preparing documents for Gensim LDA...")

        # Tokenize and clean
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        
        processed_texts = []
        for text in texts:
            if isinstance(text, str):
                tokens = [w.lower() for w in text.split() 
                         if w.isalnum() and w.lower() not in stop_words]
                processed_texts.append(tokens)
        
        # Create dictionary and corpus
        dictionary = corpora.Dictionary(processed_texts)
        corpus = [dictionary.doc2bow(text) for text in processed_texts]
        
        # Fit model
        logger.info(f"Fitting Gensim LDA model with {self.num_topics} topics...")
        self.model = models.LdaMulticore(
            corpus=corpus,
            id2word=dictionary,
            num_topics=self.num_topics,
            passes=passes,
            workers=4
        )
        
        self.vectorizer = dictionary
        logger.info("Gensim LDA model fitted successfully")
    
    def _extract_topics(self, doc_term_matrix):
        """Extract and display topics from fitted model."""
        self.topics = []
        
        for topic_idx, topic in enumerate(self.model.components_):
            top_indices = topic.argsort()[-10:][::-1]
            top_words = [self.vectorizer[i] for i in top_indices]
            weights = [topic[i] for i in top_indices]
            
            self.topics.append({
                'topic_id': topic_idx,
                'words': top_words,
                'weights': weights
            })
    
    def fit_and_analyze(
        self,
        df: pd.DataFrame,
        text_column: str = 'text'
    ) -> pd.DataFrame:
        """
        Fit model and assign topics to documents.
        
        Args:
            df: DataFrame with text data
            text_column: Column name containing text
            
        Returns:
            DataFrame with topic assignments
        """
        # Limit processing in testing mode
        if self.testing_mode and len(df) > 20:
            df = df.head(20).copy()  # Process only first 20 documents for testing
            logger.info("Testing mode: Limiting topic modeling to first 20 documents")
        
        # Handle case where text_column might be duplicated
        if isinstance(df[text_column], pd.DataFrame):
            text_series = df[text_column].iloc[:, -1]
        else:
            text_series = df[text_column]

        # Only model rows that have actual text; track their indices for alignment
        valid_mask = text_series.fillna('').astype(str).str.strip().str.len() > 0
        valid_indices = df.index[valid_mask]
        valid_texts = text_series[valid_mask].astype(str).tolist()

        # Prepare documents
        doc_term_matrix, feature_names, vectorizer = self.prepare_documents(valid_texts)

        # Fit model
        self.fit_lda(doc_term_matrix, feature_names)

        # Get topic distribution for each document
        doc_topic_dist = self.model.transform(doc_term_matrix)

        dominant_topics = np.argmax(doc_topic_dist, axis=1)
        topic_probabilities = np.max(doc_topic_dist, axis=1)

        # Write results back aligned to original indices; rows without text get NaN
        result_df = df.copy()
        result_df['topic'] = np.nan
        result_df['topic_probability'] = np.nan
        result_df.loc[valid_indices, 'topic'] = dominant_topics
        result_df.loc[valid_indices, 'topic_probability'] = topic_probabilities

        for i in range(self.num_topics):
            result_df[f'topic_{i}_prob'] = np.nan
            result_df.loc[valid_indices, f'topic_{i}_prob'] = doc_topic_dist[:, i]
        
        logger.info(f"Topics assigned to {len(result_df)} documents")
        return result_df
    
    def display_topics(self) -> List[Dict]:
        """Display extracted topics."""
        if self.topics is None:
            logger.warning("No topics extracted. Fit model first.")
            return []
        
        for topic in self.topics:
            print(f"\nTopic {topic['topic_id']}:")
            print("  Top words:")
            for word, weight in zip(topic['words'], topic['weights']):
                print(f"    {word}: {weight:.4f}")
        
        return self.topics
    
    def visualize_topics(self, output_file: str = 'output/topic_distribution.html'):
        """
        Visualize topics using pyLDAvis.
        
        Args:
            output_file: Output HTML file path
        """
        try:
            import pyLDAvis.gensim_models as gensimvis
            import pyLDAvis
            
            from gensim import models as gensim_models  # noqa: PLC0415
            if isinstance(self.model, gensim_models.LdaMulticore):
                vis = gensimvis.prepare(self.model, self.corpus, self.vectorizer)
                pyLDAvis.save_html(vis, output_file)
                logger.info(f"Topic visualization saved to {output_file}")
            else:
                logger.warning("Visualization only supported for Gensim models")
        except Exception as e:
            logger.error(f"Could not create visualization: {e}")
    
    def categorize_by_theme(self, df: pd.DataFrame, text_column: str = 'text') -> Dict[str, List[str]]:
        """
        Categorize documents into the 5 required themes (SR-01).
        Returns dict mapping theme → list of up to 5 example texts.
        """
        categorized: Dict[str, List[str]] = {theme: [] for theme in _THEME_PRIORITY}
        for _, row in df.iterrows():
            theme = assign_primary_theme(str(row.get(text_column, "")))
            if theme and len(categorized[theme]) < 5:
                categorized[theme].append(str(row.get(text_column, "")))
        return {k: v for k, v in categorized.items() if v}


if __name__ == '__main__':
    # Example usage
    sample_df = pd.DataFrame({
        'text': [
            'The dinosaur museum was fun for the kids but not much else in Fukui',
            'Kanazawa has everything Fukui has, just closer to Tokyo',
            'Getting to Fukui from Kanazawa requires multiple train changes',
            'Eiheiji temple is a spiritual oasis but hard to reach without a car',
            'The Echizen crab in Fukui is the best in Japan, definitely worth the trip'
        ]
    })
    
    model = TopicModel(num_topics=3)
    result_df = model.fit_and_analyze(sample_df)
    
    print("\nTopic Analysis Results:")
    print(result_df[['text', 'topic', 'topic_probability']])
    
    print("\n\nExtracted Topics:")
    model.display_topics()
