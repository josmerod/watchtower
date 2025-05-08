import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging import get_logger
from src.utils.file_system import get_project_root


class PersonalRecommender:
    """
    Recommender system that provides personalized recommendations based on user interests
    and interaction history.
    
    This class implements content-based filtering to recommend items (papers) that 
    match user interests and previous interactions.
    """
    
    def __init__(
        self, 
        name: str = "arxiv_recommender",
        user_profile_dir: Optional[str] = None
    ):
        """
        Initialize the recommender system.
        
        Args:
            name (str): Name for this recommender instance
            user_profile_dir (Optional[str]): Directory to store user profiles
        """
        self.name = name
        self.logger = get_logger(f"Recommender_{name}")
        
        # Initialize paths
        self.project_root = get_project_root()
        
        if user_profile_dir is None:
            user_profile_dir = os.path.join(self.project_root, "data/users/profiles")
            
        self.user_profile_dir = user_profile_dir
        
        # Ensure directory exists
        os.makedirs(self.user_profile_dir, exist_ok=True)
        
        # Initialize vectorizer for content representation
        self.vectorizer = TfidfVectorizer(
            max_df=0.7,
            min_df=2,
            stop_words='english'
        )
        
        # Cache for item features
        self.item_features = {}
        self.item_vectors = None
        self.item_ids = []
        
        self.logger.info(f"Recommender {name} initialized")
    
    def _get_user_profile_path(self, user_id: str) -> str:
        """
        Get the path to a user's profile file.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            str: Path to the user profile file
        """
        return os.path.join(self.user_profile_dir, f"{user_id}.json")
    
    def load_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Load a user profile from disk.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            Dict[str, Any]: User profile data or empty dict if not found
        """
        profile_path = self._get_user_profile_path(user_id)
        
        if not os.path.exists(profile_path):
            self.logger.info(f"User profile for {user_id} not found, creating new profile")
            return {
                "user_id": user_id,
                "interests": [],
                "viewed_items": [],
                "rated_items": {},
                "preferred_categories": [],
                "created_at": "",
                "updated_at": ""
            }
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                self.logger.info(f"Loaded profile for user {user_id}")
                return profile
        except Exception as e:
            self.logger.error(f"Error loading user profile for {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "interests": [],
                "viewed_items": [],
                "rated_items": {},
                "preferred_categories": [],
                "created_at": "",
                "updated_at": ""
            }
    
    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """
        Save a user profile to disk.
        
        Args:
            user_id (str): User identifier
            profile (Dict[str, Any]): User profile data
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile_path = self._get_user_profile_path(user_id)
        
        try:
            # Update timestamp
            from datetime import datetime
            now = datetime.now().isoformat()
            
            if not profile.get("created_at"):
                profile["created_at"] = now
                
            profile["updated_at"] = now
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Saved profile for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving user profile for {user_id}: {str(e)}")
            return False
    
    def update_user_interests(self, user_id: str, interests: List[str]) -> bool:
        """
        Update a user's interests.
        
        Args:
            user_id (str): User identifier
            interests (List[str]): List of interest keywords
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_user_profile(user_id)
        
        # Update interests, removing duplicates
        current_interests = set(profile.get("interests", []))
        updated_interests = list(current_interests.union(set(interests)))
        
        profile["interests"] = updated_interests
        
        return self.save_user_profile(user_id, profile)
    
    def record_item_view(self, user_id: str, item_id: str) -> bool:
        """
        Record that a user has viewed an item.
        
        Args:
            user_id (str): User identifier
            item_id (str): Item identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_user_profile(user_id)
        
        # Add item to viewed items if not already present
        viewed_items = profile.get("viewed_items", [])
        if item_id not in viewed_items:
            viewed_items.append(item_id)
            profile["viewed_items"] = viewed_items
            
            return self.save_user_profile(user_id, profile)
        
        return True
    
    def record_item_rating(self, user_id: str, item_id: str, rating: float) -> bool:
        """
        Record a user's rating for an item.
        
        Args:
            user_id (str): User identifier
            item_id (str): Item identifier
            rating (float): Rating value (1-5)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not 1 <= rating <= 5:
            self.logger.warning(f"Invalid rating {rating} (should be 1-5)")
            return False
            
        profile = self.load_user_profile(user_id)
        
        # Update rated items
        rated_items = profile.get("rated_items", {})
        rated_items[item_id] = rating
        profile["rated_items"] = rated_items
        
        return self.save_user_profile(user_id, profile)
    
    def update_preferred_categories(self, user_id: str, categories: List[str]) -> bool:
        """
        Update a user's preferred categories.
        
        Args:
            user_id (str): User identifier
            categories (List[str]): List of category identifiers
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_user_profile(user_id)
        
        # Update preferred categories, removing duplicates
        current_categories = set(profile.get("preferred_categories", []))
        updated_categories = list(current_categories.union(set(categories)))
        
        profile["preferred_categories"] = updated_categories
        
        return self.save_user_profile(user_id, profile)
    
    def load_items(self, items: List[Dict[str, Any]]) -> bool:
        """
        Load item data into the recommender.
        
        Args:
            items (List[Dict[str, Any]]): List of items (papers)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not items:
            self.logger.warning("No items provided to load")
            return False
        
        try:
            # Extract text features from items for content-based filtering
            item_texts = []
            item_ids = []
            
            for item in items:
                item_id = item.get("id")
                title = item.get("title", "")
                summary = item.get("summary", "")
                
                # Also include cluster keywords and categories if available
                cluster_keywords = ", ".join(item.get("cluster_keywords", []))
                categories = ", ".join(item.get("categories", []))
                
                # Combine all text features
                text = f"{title} {summary} {cluster_keywords} {categories}"
                
                item_texts.append(text)
                item_ids.append(item_id)
                
                # Store the original item for later reference
                self.item_features[item_id] = item
            
            # Fit vectorizer and transform texts to feature vectors
            item_vectors = self.vectorizer.fit_transform(item_texts)
            
            self.item_vectors = item_vectors
            self.item_ids = item_ids
            
            self.logger.info(f"Loaded {len(items)} items into recommender")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading items: {str(e)}")
            return False
    
    def _calculate_user_vector(self, profile: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Calculate a user's interest vector based on their profile.
        
        Args:
            profile (Dict[str, Any]): User profile
            
        Returns:
            Tuple[np.ndarray, float]: User interest vector and confidence score
        """
        if not self.item_vectors:
            self.logger.error("No items loaded in recommender")
            return None, 0.0
        
        # Extract user interests and seen items
        interests = profile.get("interests", [])
        viewed_items = profile.get("viewed_items", [])
        rated_items = profile.get("rated_items", {})
        preferred_categories = profile.get("preferred_categories", [])
        
        # Calculate weights for different profile components
        interest_weight = 1.0
        viewed_weight = 0.5
        rating_weight = 2.0
        category_weight = 1.5
        
        # Initialize user vector
        user_vector = np.zeros(self.item_vectors.shape[1])
        components = 0
        
        # Add interest terms
        if interests:
            try:
                interest_text = " ".join(interests)
                interest_vector = self.vectorizer.transform([interest_text])
                user_vector += interest_weight * interest_vector.toarray()[0]
                components += 1
            except Exception as e:
                self.logger.error(f"Error processing interests: {str(e)}")
        
        # Add vectors from viewed items
        if viewed_items:
            viewed_vectors = []
            for item_id in viewed_items:
                if item_id in self.item_ids:
                    idx = self.item_ids.index(item_id)
                    viewed_vectors.append(self.item_vectors[idx])
            
            if viewed_vectors:
                viewed_centroid = np.mean(np.vstack([v.toarray() for v in viewed_vectors]), axis=0)
                user_vector += viewed_weight * viewed_centroid
                components += 1
        
        # Add vectors from rated items (weighted by rating)
        if rated_items:
            rated_vectors = []
            weights = []
            
            for item_id, rating in rated_items.items():
                if item_id in self.item_ids:
                    idx = self.item_ids.index(item_id)
                    rated_vectors.append(self.item_vectors[idx].toarray()[0])
                    # Convert rating to weight (1-5 scale to 0.2-1.0)
                    weight = rating / 5.0
                    weights.append(weight)
            
            if rated_vectors:
                # Weighted average of rated item vectors
                rated_centroid = np.average(
                    np.vstack(rated_vectors),
                    axis=0, 
                    weights=weights
                )
                user_vector += rating_weight * rated_centroid
                components += 1
        
        # Add preferred categories
        if preferred_categories:
            try:
                category_text = " ".join(preferred_categories)
                category_vector = self.vectorizer.transform([category_text])
                user_vector += category_weight * category_vector.toarray()[0]
                components += 1
            except Exception as e:
                self.logger.error(f"Error processing categories: {str(e)}")
        
        # Calculate confidence based on profile completeness
        confidence = min(1.0, components / 4.0)
        
        # Normalize user vector
        norm = np.linalg.norm(user_vector)
        if norm > 0:
            user_vector = user_vector / norm
        
        return user_vector, confidence
    
    def recommend_for_user(
        self,
        user_id: str,
        n_recommendations: int = 10,
        exclude_viewed: bool = True,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for a user.
        
        Args:
            user_id (str): User identifier
            n_recommendations (int): Number of recommendations to generate
            exclude_viewed (bool): Whether to exclude items the user has already viewed
            min_similarity (float): Minimum similarity threshold
            
        Returns:
            List[Dict[str, Any]]: List of recommended items with similarity scores
        """
        if not self.item_vectors:
            self.logger.error("No items loaded in recommender")
            return []
        
        # Load user profile
        profile = self.load_user_profile(user_id)
        
        # Get user interest vector
        user_vector, confidence = self._calculate_user_vector(profile)
        
        if user_vector is None:
            self.logger.warning(f"Could not calculate interest vector for user {user_id}")
            return []
        
        # If confidence is too low, use a fallback strategy
        if confidence < 0.2:
            self.logger.info(f"Low confidence ({confidence}) for user {user_id}, using fallback recommendations")
            return self._fallback_recommendations(n_recommendations)
        
        # Calculate similarities to all items
        similarities = []
        
        for i, item_id in enumerate(self.item_ids):
            item_vector = self.item_vectors[i]
            sim = cosine_similarity(user_vector.reshape(1, -1), item_vector)[0][0]
            
            # Skip items with low similarity
            if sim < min_similarity:
                continue
                
            # Skip viewed items if requested
            if exclude_viewed and item_id in profile.get("viewed_items", []):
                continue
                
            similarities.append({
                "item_id": item_id,
                "similarity": float(sim),
                "item": self.item_features[item_id]
            })
        
        # Sort by similarity (descending)
        sorted_similarities = sorted(
            similarities,
            key=lambda x: x["similarity"],
            reverse=True
        )
        
        # Return top N
        return sorted_similarities[:n_recommendations]
    
    def _fallback_recommendations(self, n_recommendations: int = 10) -> List[Dict[str, Any]]:
        """
        Generate fallback recommendations when user profile is insufficient.
        
        Args:
            n_recommendations (int): Number of recommendations to generate
            
        Returns:
            List[Dict[str, Any]]: List of recommended items
        """
        # If we have no user profile, return random items with high citation count,
        # recent publication date, or other general quality indicators
        
        # For now, just return random items
        import random
        
        if not self.item_features:
            return []
            
        item_ids = list(self.item_features.keys())
        if len(item_ids) <= n_recommendations:
            selected_ids = item_ids
        else:
            selected_ids = random.sample(item_ids, n_recommendations)
            
        recommendations = []
        for item_id in selected_ids:
            recommendations.append({
                "item_id": item_id,
                "similarity": 0.0,  # No real similarity for random recommendations
                "item": self.item_features[item_id]
            })
            
        return recommendations 