document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const imageInput = document.getElementById('imageInput');
    const uploadedImage = document.getElementById('uploadedImage');
    const loadingDiv = document.getElementById('loading');
    const resultsContainer = document.getElementById('resultsContainer');
    
    // Result elements
    const model1Name = document.getElementById('model1Name');
    const model1Text = document.getElementById('model1Text');
    const model2Name = document.getElementById('model2Name');
    const model2Text = document.getElementById('model2Text');
    const comparisonResult = document.getElementById('comparisonResult');
    const consensusResult = document.getElementById('consensusResult');

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const file = imageInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Image = reader.result.split(',')[1];
                uploadedImage.src = reader.result;
                uploadedImage.style.display = 'block';
                
                // Show loading, hide results
                loadingDiv.style.display = 'block';
                resultsContainer.style.display = 'none';

                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ image_data: base64Image }),
                    });

                    if (response.ok) {
                        const data = await response.json();
                        
                        // Display results
                        model1Name.textContent = data.model1.name;
                        model1Text.textContent = data.model1.result;
                        
                        model2Name.textContent = data.model2.name;
                        model2Text.textContent = data.model2.result;
                        
                        comparisonResult.innerHTML = data.comparison;
                        consensusResult.textContent = data.consensus;
                        
                        // Show results, hide loading
                        loadingDiv.style.display = 'none';
                        resultsContainer.style.display = 'block';
                    } else {
                        throw new Error(`${response.status} - ${await response.text()}`);
                    }
                } catch (error) {
                    console.error('Error sending request:', error);
                    loadingDiv.style.display = 'none';
                    alert('Failed to analyze image. Please try again.');
                }
            };
            reader.readAsDataURL(file);
        } else {
            alert('Please select an image file.');
        }
    });
});
