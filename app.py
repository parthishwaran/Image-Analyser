from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import base64
from difflib import SequenceMatcher
from collections import defaultdict
import re

app = Flask(__name__)

# Replace with your actual OpenRouter API Key
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODEL_1 = "google/gemini-2.0-flash-exp:free"
MODEL_2 = "opengvlab/internvl3-14b:free"  # Second model to compare

client = OpenAI(
    base_url=OPENROUTER_URL,
    api_key=OPENROUTER_API_KEY,
)

def analyze_with_model(image_data_base64, model_name):
    """Analyzes an image using a specific language model via OpenRouter."""
    try:
        data_url = f"data:image/jpeg;base64,{image_data_base64}"

        prompt = """Analyze this image for all discernible objects. For each object, provide:

- **Identification:** A clear name (e.g., red apple, woman, blue car, three trees).
- **Location:** Its position in the image (e.g., center, left, background, next to...).
- **Details:**
    - **Non-living:** Color(s) and notable characteristics (e.g., shiny silver laptop, weathered wooden fence). If multiple, include a count (e.g., three green leaves).
    - **Humans:** Estimated gender (woman, man, person), age group (infant, child, teenager, adult, elderly), and any prominent features or actions (e.g., smiling woman, child playing ball).
    - **Animals:** Species (e.g., brown dog, grey cat, flock of birds), color(s), actions/postures (e.g., sleeping cat, bird flying). If multiple, include a count.
    - **Plants:** Type if identifiable (e.g., green tree, red flower, patches of grass), color(s), and notable features (e.g., tall tree with many leaves, vibrant red rose). If multiple, include a count.

Structure your response as a concise list of these object descriptions."""
        
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            max_tokens=30000,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error during analysis with {model_name}: {e}"

def parse_object_descriptions(text):
    """Parse the object descriptions from the model output."""
    objects = []
    current_object = {}
    
    # Split by lines and process
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check for identification
        if line.startswith('- **Identification:**'):
            if current_object:
                objects.append(current_object)
            current_object = {'identification': line.replace('- **Identification:**', '').strip()}
        elif line.startswith('- **Location:'):
            current_object['location'] = line.replace('- **Location:**', '').strip()
        elif line.startswith('- **Details:'):
            current_object['details'] = line.replace('- **Details:**', '').strip()
        elif current_object and 'details' in current_object:
            # Append to details if we're in details section
            current_object['details'] += '\n' + line
    
    if current_object:
        objects.append(current_object)
    
    return objects

def generate_consensus(result1, result2):
    """Generate a consensus output from both model results."""
    # Parse both results into structured data
    objects1 = parse_object_descriptions(result1)
    objects2 = parse_object_descriptions(result2)
    
    # Create a combined list of all objects
    all_objects = objects1 + objects2
    
    # Group similar objects together
    object_groups = defaultdict(list)
    for obj in all_objects:
        # Simple grouping by identification (could be enhanced with NLP)
        key = obj['identification'].lower()
        object_groups[key].append(obj)
    
    # Generate consensus for each group
    consensus_objects = []
    for group_name, group_objects in object_groups.items():
        if not group_objects:
            continue
            
        # Take the most detailed version of each object
        most_detailed = max(group_objects, key=lambda x: len(x.get('details', '')))
        
        consensus_obj = {
            'identification': most_detailed['identification'],
            'location': most_detailed.get('location', 'Not specified'),
            'details': most_detailed.get('details', 'No details provided')
        }
        
        # If we have multiple versions, note this in the details
        if len(group_objects) > 1:
            consensus_obj['details'] += f"\n\n(Note: {len(group_objects)} versions of this object were identified across models)"
        
        consensus_objects.append(consensus_obj)
    
    # Format the consensus output
    consensus_output = "## Consensus Analysis (Combined Best Results)\n\n"
    for obj in consensus_objects:
        consensus_output += f"- **Identification:** {obj['identification']}\n"
        consensus_output += f"  - **Location:** {obj['location']}\n"
        consensus_output += f"  - **Details:** {obj['details']}\n\n"
    
    return consensus_output.strip()

def compare_analyses(result1, result2):
    """Compares two analysis results and provides insights."""
    similarity = SequenceMatcher(None, result1, result2).ratio()
    
    analysis = f"""
    <h3>Comparison Analysis</h3>
    <p><strong>Similarity Score:</strong> {similarity:.2%}</p>
    
    <h4>Key Observations:</h4>
    <ul>
        <li>The models agree on {similarity:.0%} of the content</li>
        <li>Model 1 (Gemini) provided {len(result1.split())} words</li>
        <li>Model 2 (Claude) provided {len(result2.split())} words</li>
    </ul>
    """
    
    return analysis

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    image_data_base64 = data.get('image_data')

    if not image_data_base64:
        return jsonify({'error': 'No image data received'}), 400

    # Get results from both models
    result1 = analyze_with_model(image_data_base64, MODEL_1)
    result2 = analyze_with_model(image_data_base64, MODEL_2)
    
    # Compare the results and generate consensus
    comparison = compare_analyses(result1, result2)
    consensus = generate_consensus(result1, result2)
    
    return jsonify({
        'model1': {'name': MODEL_1, 'result': result1},
        'model2': {'name': MODEL_2, 'result': result2},
        'comparison': comparison,
        'consensus': consensus
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
