"""NLP Content Classifier for text analysis and clustering.

This module provides the `NLPContentClassifier` class, which uses
TF-IDF vectorization, dimensionality reduction (LSA), and K-Means clustering
to classify text documents, extract keywords, and identify topics.
"""
import os
import json
import nltk
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

import sys
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root


class NLPContentClassifier:
    """
    NLP-based classifier for text content.
    
    This class provides utilities to:
    1. Extract keywords from text
    2. Cluster similar documents
    3. Generate topic labels
    """
    
    def __init__(self, name: str = "nlp_classifier"):
        """
        Initialize the NLP content classifier.
        
        Args:
            name (str): Name of the classifier, used for logging and storing models
        """
        self.name = name
        self.logger = get_logger(f"NLP_{name}")
        
        # Ensure necessary NLTK data is available
        self._download_nltk_resources()
        
        # Paths for storing models and data
        self.project_root = get_project_root()
        self.models_dir = os.path.join(self.project_root, f"data/models/nlp/{self.name}")
        ensure_directories([f"data/models/nlp/{self.name}"])
        
        # Initialize models
        self.vectorizer = None
        self.dimension_reducer = None
        self.clustering = None
        self.top_keywords_per_cluster = {}
        
    def _download_nltk_resources(self):
        """Download necessary NLTK resources."""
        resources = [
            ('punkt', 'tokenizers/punkt'),
            ('stopwords', 'corpora/stopwords'),
            ('wordnet', 'corpora/wordnet'),
            ('averaged_perceptron_tagger', 'taggers/averaged_perceptron_tagger'),
            ('averaged_perceptron_tagger_eng', 'taggers/averaged_perceptron_tagger_eng'), # Added specifically
            ('punkt_tab', 'tokenizers/punkt_tab')
        ]
        
        for resource_name, resource_path in resources:
            try:
                # nltk.data.find checks various paths for the resource
                nltk.data.find(resource_path)
            except LookupError:
                self.logger.info(f"Downloading NLTK resource: {resource_name}")
                nltk.download(resource_name, quiet=True)
        
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract most important keywords from text.
        
        Args:
            text (str): Input text
            top_n (int): Number of keywords to extract
            
        Returns:
            List[str]: List of top keywords
        """
        # Tokenize and convert to lowercase
        tokens = nltk.word_tokenize(text.lower())
        
        # Remove stopwords, punctuation, and short words
        stop_words = set(nltk.corpus.stopwords.words('english'))
        tokens = [
            word for word in tokens 
            if word.isalnum() and 
            word not in stop_words and 
            len(word) > 2
        ]
        
        # Get part-of-speech tags
        pos_tags = nltk.pos_tag(tokens)
        
        # Keep only nouns and adjectives as keywords are often these types
        keywords = [
            word for word, pos in pos_tags 
            if pos.startswith('NN') or pos.startswith('JJ')
        ]
        
        # Count occurrences and get top keywords
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(top_n)]
        
    def train_classifier(self, texts: List[str], n_clusters: int = 10):
        """
        Train the classifier using a collection of texts.
        
        Args:
            texts (List[str]): List of text documents to train on
            n_clusters (int): Number of clusters to create
        """
        self.logger.info(f"Training classifier with {len(texts)} documents")
        
        # Create TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_df=0.5,          # Ignore terms that appear in more than 50% of docs
            min_df=2,            # Ignore terms that appear in fewer than 2 docs
            use_idf=True,        # Use inverse document frequency weighting
            stop_words='english'
        )
        
        # Create dimensionality reduction component (LSA)
        # Reduce to 100 dimensions or fewer if we have fewer docs
        n_components = min(100, len(texts) - 1)
        self.dimension_reducer = TruncatedSVD(n_components=n_components)
        
        # Create normalizer
        normalizer = Normalizer(copy=False)
        
        # Create clustering component
        self.clustering = KMeans(
            n_clusters=min(n_clusters, len(texts)),  # Don't create more clusters than docs
            random_state=42
        )
        
        # Create and apply the pipeline
        lsa_pipeline = Pipeline([
            ('tfidf', self.vectorizer),
            ('svd', self.dimension_reducer),
            ('normalizer', normalizer)
        ])
        
        # Transform documents to LSA space
        X_lsa = lsa_pipeline.fit_transform(texts)
        
        # Cluster documents
        self.clustering.fit(X_lsa)
        
        # Extract top keywords for each cluster
        self._extract_cluster_keywords(texts)
        
        self.logger.info("Classifier training completed")
        
    def _extract_cluster_keywords(self, texts: List[str], top_n: int = 10):
        """
        Extract top keywords that characterize each cluster.
        
        Args:
            texts (List[str]): The texts used for training
            top_n (int): Number of top keywords to extract per cluster
        """
        # Get cluster assignments for each document
        if self.clustering is None or self.vectorizer is None:
            self.logger.error("Classifier not trained yet")
            return
            
        # Get tfidf matrix
        X = self.vectorizer.transform(texts)
        cluster_labels = self.clustering.labels_
        
        # Get feature names from vectorizer
        feature_names = np.array(self.vectorizer.get_feature_names_out())
        
        # For each cluster, find top keywords
        self.top_keywords_per_cluster = {}
        
        for cluster_id in range(self.clustering.n_clusters):
            # Get indices of documents in this cluster
            doc_indices = np.where(cluster_labels == cluster_id)[0]
            
            if len(doc_indices) > 0:
                # Get mean tfidf values for this cluster
                cluster_tfidf_mean = X[doc_indices].mean(axis=0).A1
                
                # Get indices of top terms for this cluster
                top_indices = cluster_tfidf_mean.argsort()[-top_n:][::-1]
                
                # Get the actual terms
                top_terms = feature_names[top_indices].tolist()
                
                self.top_keywords_per_cluster[cluster_id] = top_terms
                
        self.logger.info(f"Extracted top {top_n} keywords for {len(self.top_keywords_per_cluster)} clusters")
        
    def get_cluster_labels(self) -> Dict[int, str]:
        """
        Generate human-readable labels for each cluster.
        
        Returns:
            Dict[int, str]: Mapping of cluster IDs to labels
        """
        if not self.top_keywords_per_cluster:
            self.logger.error("No cluster keywords extracted yet")
            return {}
            
        cluster_labels = {}
        
        for cluster_id, keywords in self.top_keywords_per_cluster.items():
            # Use top 3 keywords as the label
            label = " | ".join(keywords[:3])
            cluster_labels[cluster_id] = label
            
        return cluster_labels
        
    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classify a document into a cluster and extract its keywords.
        
        Args:
            text (str): Text to classify
            
        Returns:
            Dict[str, Any]: Classification results including:
                - cluster_id: ID of the assigned cluster
                - cluster_keywords: Top keywords for the assigned cluster
                - document_keywords: Top keywords extracted from the document
        """
        if self.clustering is None or self.vectorizer is None:
            self.logger.error("Classifier not trained yet")
            return {"error": "Classifier not trained"}
            
        # Extract document keywords
        document_keywords = self.extract_keywords(text, top_n=10)
        
        # Transform the document
        X = self.vectorizer.transform([text])
        X_lsa = self.dimension_reducer.transform(X)
        X_normalized = Normalizer(copy=False).transform(X_lsa)
        
        # Predict cluster
        cluster_id = int(self.clustering.predict(X_normalized)[0])
        
        # Get cluster keywords
        cluster_keywords = self.top_keywords_per_cluster.get(
            cluster_id, ["unknown"]
        )
        
        # Get cluster label
        cluster_label = " | ".join(cluster_keywords[:3])
        
        return {
            "cluster_id": cluster_id,
            "cluster_label": cluster_label,
            "cluster_keywords": cluster_keywords,
            "document_keywords": document_keywords
        }
        
    def batch_classify(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Classify a batch of documents.
        
        Args:
            texts (List[str]): Texts to classify
            
        Returns:
            List[Dict[str, Any]]: Classification results for each document
        """
        if self.clustering is None or self.vectorizer is None:
            self.logger.error("Classifier not trained yet")
            return [{"error": "Classifier not trained"} for _ in texts]
            
        results = []
        
        # Transform all documents at once (more efficient)
        X = self.vectorizer.transform(texts)
        X_lsa = self.dimension_reducer.transform(X)
        X_normalized = Normalizer(copy=False).transform(X_lsa)
        
        # Predict clusters
        cluster_ids = self.clustering.predict(X_normalized)
        
        # Process each document
        for i, text in enumerate(texts):
            cluster_id = int(cluster_ids[i])
            document_keywords = self.extract_keywords(text, top_n=10)
            cluster_keywords = self.top_keywords_per_cluster.get(
                cluster_id, ["unknown"]
            )
            cluster_label = " | ".join(cluster_keywords[:3])
            
            results.append({
                "cluster_id": cluster_id,
                "cluster_label": cluster_label,
                "cluster_keywords": cluster_keywords,
                "document_keywords": document_keywords
            })
            
        return results
        
    def save_model(self, filepath: Optional[str] = None):
        """
        Save the trained model to disk.
        
        Args:
            filepath (Optional[str]): Path to save the model, or None to use default path
        """
        if self.vectorizer is None or self.clustering is None:
            self.logger.error("No trained model to save")
            return
            
        if filepath is None:
            filepath = os.path.join(self.models_dir, "model.pkl")
            
        model_data = {
            "vectorizer": self.vectorizer,
            "dimension_reducer": self.dimension_reducer,
            "clustering": self.clustering,
            "top_keywords_per_cluster": self.top_keywords_per_cluster
        }
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            
    def load_model(self, filepath: Optional[str] = None):
        """
        Load a trained model from disk.
        
        Args:
            filepath (Optional[str]): Path to the saved model, or None to use default path
        """
        if filepath is None:
            filepath = os.path.join(self.models_dir, "model.pkl")
            
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
                
            self.vectorizer = model_data["vectorizer"]
            self.dimension_reducer = model_data["dimension_reducer"]
            self.clustering = model_data["clustering"]
            self.top_keywords_per_cluster = model_data["top_keywords_per_cluster"]
            
            self.logger.info(f"Model loaded from {filepath}")
            return True
        except FileNotFoundError:
            self.logger.warning(f"Model file not found: {filepath}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return False 