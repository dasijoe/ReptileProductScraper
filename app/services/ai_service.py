"""
AI service for product categorization and analysis.
"""
import os
import json
import logging
from openai import OpenAI
from app.config import PRODUCT_CATEGORIES, REPTILE_KEYWORDS, EXCLUDE_KEYWORDS
from app.models import Category

class AIService:
    """
    Service for AI-powered operations like categorization and content analysis.
    """
    def __init__(self):
        """
        Initialize the AI service with API key.
        """
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            logging.info("AI service initialized with API key")
        else:
            logging.warning("OpenAI API key not found, AI features will be limited")
    
    def categorize_product(self, product_data):
        """
        Categorize a product using AI.
        
        Args:
            product_data: Dict with product information (name, description, etc.)
            
        Returns:
            Dict with category_name and confidence_score
        """
        if not self.client:
            # Fallback to keyword-based categorization
            return self._keyword_categorization(product_data)
        
        try:
            # Prepare product data and categories for classification
            product_text = f"Product Name: {product_data.get('name', '')}\n"
            if product_data.get('description'):
                product_text += f"Description: {product_data.get('description')}\n"
            
            categories_list = "\n".join([f"- {cat}" for cat in PRODUCT_CATEGORIES])
            
            # Prompt for the AI
            prompt = f"""
            Analyze this reptile or exotic pet product and classify it into the most appropriate category.
            
            {product_text}
            
            Available categories:
            {categories_list}
            
            First, determine if this is actually a reptile/exotic pet product. If it's for dogs, cats, or other common pets, respond with "Not a reptile product".
            
            If it is a reptile product, respond in JSON format:
            {{
                "category": "selected category name from the list",
                "confidence": a number between 0 and 1 indicating confidence,
                "reasoning": "brief explanation for this classification"
            }}
            """
            
            # Query the OpenAI API for classification
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.1
            )
            
            # Process the response
            result_text = response.choices[0].message.content
            
            # If it's not a reptile product
            if "Not a reptile product" in result_text:
                return {"category_name": None, "confidence_score": 0.0}
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                category_name = result.get("category")
                confidence_score = result.get("confidence", 0.0)
                
                # Validate category exists
                category = Category.find_by_name(category_name)
                if not category and category_name:
                    category_name = "Uncategorized"
                    confidence_score = 0.1
                
                return {
                    "category_name": category_name,
                    "confidence_score": confidence_score
                }
            except json.JSONDecodeError:
                logging.error(f"Failed to parse AI response: {result_text}")
                return self._keyword_categorization(product_data)
                
        except Exception as e:
            logging.error(f"Error in AI categorization: {str(e)}")
            return self._keyword_categorization(product_data)
    
    def _keyword_categorization(self, product_data):
        """
        Fallback method for categorization using keywords.
        """
        name = product_data.get('name', '').lower()
        description = product_data.get('description', '').lower()
        combined_text = f"{name} {description}"
        
        # Check if this is even a reptile product
        is_reptile_product = False
        for keyword in REPTILE_KEYWORDS:
            if keyword.lower() in combined_text:
                is_reptile_product = True
                break
        
        # Check exclusions
        for keyword in EXCLUDE_KEYWORDS:
            if keyword.lower() in combined_text:
                is_reptile_product = False
                break
        
        if not is_reptile_product:
            return {"category_name": None, "confidence_score": 0.0}
        
        # Simple keyword matching for categories
        matches = {}
        for category_name in PRODUCT_CATEGORIES:
            category_keywords = category_name.lower().split()
            match_score = 0
            
            for keyword in category_keywords:
                if keyword in combined_text:
                    match_score += 1
            
            if match_score > 0:
                matches[category_name] = match_score
        
        # Find best match
        if matches:
            best_category = max(matches.items(), key=lambda x: x[1])
            return {
                "category_name": best_category[0],
                "confidence_score": min(best_category[1] / 5, 0.8)  # Scale confidence
            }
        
        # Default to uncategorized
        return {"category_name": "Uncategorized", "confidence_score": 0.1}
    
    def is_reptile_product(self, product_data):
        """
        Determine if a product is a reptile/exotic pet product.
        
        Args:
            product_data: Dict with product information
            
        Returns:
            Boolean indicating if this is a reptile product
        """
        # This could be expanded to use AI for more advanced filtering
        name = product_data.get('name', '').lower()
        description = product_data.get('description', '').lower()
        combined_text = f"{name} {description}"
        
        # Check reptile keywords
        is_reptile = False
        for keyword in REPTILE_KEYWORDS:
            if keyword.lower() in combined_text:
                is_reptile = True
                break
        
        # Check exclusion keywords
        if is_reptile:
            for keyword in EXCLUDE_KEYWORDS:
                if keyword.lower() in combined_text:
                    is_reptile = False
                    break
        
        return is_reptile
