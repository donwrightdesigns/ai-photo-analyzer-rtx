#!/usr/bin/env python3
"""
Photography Taxonomy System - Centralized taxonomies for AI Image Analyzer

Provides standardized photography-specific taxonomies for all analyzers:
- Categories and subcategories
- Subject, lighting, style, event/location, and mood tags  
- Personas and evaluation criteria
- JSON templates for consistent output

Used by: pipeline_core.py, llava_standalone_analyzer.py, and other analyzers
"""

# Main Categories (3 broad classifications)
CATEGORIES = ["People", "Place", "Thing"]

# Detailed Subcategories (comprehensive photo subjects)
SUB_CATEGORIES = [
    "Portrait", "Group-Shot", "Couple", "Family", "Children", "Baby", "Senior-Citizen",
    "Pet", "Wildlife", "Bird", "Automotive", "Architecture", "Interior", "Product", 
    "Food", "Flowers", "Macro", "Landscape", "Urban", "Beach", "Forest", "Event"
]

# Photography-Specific Tag Categories
SUBJECT_TAGS = [
    "Portrait", "Group-Shot", "Couple", "Family", "Children", "Baby", "Senior-Citizen",
    "Pet", "Wildlife", "Bird", "Automotive", "Architecture", "Interior", "Product",
    "Food", "Flowers", "Macro"
]

LIGHTING_TAGS = [
    "Golden-Hour", "Blue-Hour", "Overcast", "Direct-Sun", "Window-Light",
    "Studio-Strobe", "Speedlight", "Natural-Light", "Low-Light", "Backlit",
    "Side-Lit", "Dramatic-Lighting"
]

STYLE_TAGS = [
    "Black-White", "Color-Graded", "High-Contrast", "Soft-Focus", "Sharp-Detail",
    "Shallow-DOF", "Wide-Angle", "Telephoto", "Candid", "Posed", "Action-Shot", "Still-Life"
]

EVENT_LOCATION_TAGS = [
    "Wedding", "Engagement", "Corporate", "Real-Estate", "Landscape",
    "Urban", "Beach", "Forest", "Indoor", "Outdoor", "Studio", "Event",
    "Concert", "Sports"
]

MOOD_TAGS = [
    "Bright-Cheerful", "Moody-Dark", "Romantic", "Professional", "Casual",
    "Energetic", "Peaceful", "Dramatic"
]

# Combined tag list for selection
ALL_TAGS = SUBJECT_TAGS + LIGHTING_TAGS + STYLE_TAGS + EVENT_LOCATION_TAGS + MOOD_TAGS

# Photographer Personas and Evaluation Criteria
PHOTOGRAPHER_PERSONAS = {
    'professional_art_critic': {
        'name': 'Professional Art Critic',
        'persona': 'You are a professional art critic and gallery curator with 25 years of experience, evaluating photographs for potential inclusion in a fine art exhibition.',
        'criteria': [
            'Technical Excellence: Focus, exposure, composition, color/lighting',
            'Artistic Merit: Creativity, emotional impact, visual storytelling', 
            'Commercial Appeal: Marketability, broad audience appeal',
            'Uniqueness: What sets this image apart from typical photography'
        ]
    },
    'street_photographer': {
        'name': 'Street Photographer',
        'persona': 'You are a seasoned street photographer with a keen eye for capturing authentic, spontaneous moments in urban environments.',
        'criteria': [
            'Authenticity: Genuine, unposed moments and natural expressions',
            'Composition: Use of leading lines, framing, and urban geometry',
            'Human Connection: Emotional connection with subjects and environment',
            'Decisive Moment: Capturing fleeting, significant instants'
        ]
    },
    'commercial_photographer': {
        'name': 'Commercial Photographer', 
        'persona': 'You are a commercial photographer specializing in creating images that sell products, services, and build brand identity.',
        'criteria': [
            'Brand Alignment: Does the image fit the intended brand aesthetic?',
            'Product Showcase: How effectively is the subject presented?',
            'Marketing Appeal: Does the image drive consumer interest?',
            'Professional Quality: Technical excellence for commercial use'
        ]
    },
    'photojournalist': {
        'name': 'Photojournalist',
        'persona': 'You are an experienced photojournalist dedicated to documenting events and telling compelling stories through powerful imagery.',
        'criteria': [
            'Newsworthiness: Does the image capture a significant moment or event?',
            'Objectivity: Fair and accurate representation without bias',
            'Emotional Impact: Strong emotional response that supports the story',
            'Narrative Clarity: Does the image tell a clear, compelling story?'
        ]
    },
    'social_media_influencer': {
        'name': 'Social Media Influencer',
        'persona': 'You are a social media expert with expertise in creating viral content and understanding what engages modern digital audiences.',
        'criteria': [
            'Scroll-Stopping Power: Immediately captivating and attention-grabbing',
            'Shareability: Relatable content that encourages sharing',
            'Trend Awareness: Taps into current visual trends and aesthetics',
            'Engagement Potential: Likely to generate likes, comments, and interaction'
        ]
    }
}

def get_analysis_prompt(profile_key='professional_art_critic', include_critique=False):
    """
    Generate analysis prompt based on photographer persona.
    
    Args:
        profile_key (str): Key for photographer persona
        include_critique (bool): Whether to include critique in JSON template
        
    Returns:
        str: Complete analysis prompt with taxonomy and JSON template
    """
    profile = PHOTOGRAPHER_PERSONAS.get(profile_key, PHOTOGRAPHER_PERSONAS['professional_art_critic'])
    
    # Build criteria text
    criteria_text = "\\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(profile['criteria'])])
    
    # Build JSON template
    json_template = {
        "category": "chosen_category",
        "subcategory": "chosen_subcategory", 
        "tags": ["tag1", "tag2", "tag3"],
        "score": 7
    }
    
    if include_critique:
        json_template["critique"] = f"Professional critique from {profile['name']} perspective."
    
    import json
    json_str = json.dumps(json_template, indent=2)
    
    prompt = f"""
{profile['persona']}

ANALYSIS CRITERIA:
{criteria_text}

CLASSIFICATION (select ONE from each category):
CATEGORIES: {', '.join(CATEGORIES)}
SUB_CATEGORIES: {', '.join(SUB_CATEGORIES)}
TAGS: {', '.join(ALL_TAGS)} (select 2-4 most relevant)

SCORING GUIDE (1-10 scale from {profile['name']} perspective):
1-2: Poor (fails to meet basic standards for this evaluation type)
3-4: Below Average (basic competence, limited value for intended purpose)
5-6: Average (meets standard expectations for this type of image)
7-8: Above Average (strong quality and purpose alignment)
9-10: Exceptional (outstanding example that excels in all criteria)

RESPOND WITH VALID JSON ONLY:
{json_str}
"""
    
    return prompt

def get_archive_culling_prompt():
    """
    Get prompt specifically for archive culling/quality assessment.
    
    Returns:
        dict: Dictionary of analysis prompts for different aspects
    """
    return {
        "keep_score": """
        Rate this image from 1-5 stars for archival value. Consider:
        - Technical quality (focus, exposure, composition) 
        - Uniqueness (is this likely a duplicate or similar to others?)
        - Content importance (memorable moments, people, places)
        
        Rating scale:
        1 star: Poor quality, delete/cull
        2 stars: Below average, low priority
        3 stars: Average, good for archive
        4 stars: Above average, notable quality
        5 stars: Exceptional, gallery-worthy
        
        Return only a number 1-5 and brief reason.
        """,
        "quick_tags": f"""
        Provide 3-5 SPECIFIC photography keywords that a photographer would search for.
        
        CHOOSE FROM THESE PHOTOGRAPHY-SPECIFIC TAGS:
        
        SUBJECTS: {', '.join(SUBJECT_TAGS)}
        
        LIGHTING: {', '.join(LIGHTING_TAGS)}
        
        STYLE: {', '.join(STYLE_TAGS)}
        
        EVENT/LOCATION: {', '.join(EVENT_LOCATION_TAGS)}
        
        MOOD: {', '.join(MOOD_TAGS)}
        
        Return as comma-separated list.
        """
    }

def get_taxonomy_info():
    """
    Get complete taxonomy information for display/debugging.
    
    Returns:
        dict: Complete taxonomy structure
    """
    return {
        'categories': CATEGORIES,
        'sub_categories': SUB_CATEGORIES,
        'subject_tags': SUBJECT_TAGS,
        'lighting_tags': LIGHTING_TAGS,
        'style_tags': STYLE_TAGS,
        'event_location_tags': EVENT_LOCATION_TAGS,
        'mood_tags': MOOD_TAGS,
        'all_tags': ALL_TAGS,
        'personas': list(PHOTOGRAPHER_PERSONAS.keys()),
        'total_tags': len(ALL_TAGS),
        'total_subcategories': len(SUB_CATEGORIES)
    }

if __name__ == "__main__":
    # Test the taxonomy system
    import json
    
    print("🎯 Photography Taxonomy System")
    print("=" * 40)
    
    info = get_taxonomy_info()
    print(f"Categories: {len(info['categories'])}")
    print(f"Subcategories: {len(info['sub_categories'])}")
    print(f"Total Tags: {len(info['all_tags'])}")
    print(f"Personas: {len(info['personas'])}")
    
    print("\n📝 Sample Analysis Prompt:")
    print("-" * 30)
    prompt = get_analysis_prompt('professional_art_critic', include_critique=True)
    print(prompt[:200] + "...")
    
    print("\n🗂️ Archive Culling Prompts:")
    print("-" * 30)
    archive_prompts = get_archive_culling_prompt()
    for key, prompt in archive_prompts.items():
        print(f"{key}: {prompt[:100]}...")
