// Image upload functionality for document generator
document.addEventListener('DOMContentLoaded', function() {
    // Basic reset button styles - add these dynamically to ensure they're available
    const style = document.createElement('style');
    style.textContent = `
        .reset-image {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid #ddd;
            border-radius: 50%;
            width: 25px;
            height: 25px;
            font-size: 16px;
            line-height: 1;
            cursor: pointer;
            display: none;
            z-index: 10;
        }
        .reset-image:hover {
            background: rgba(255, 255, 255, 0.9);
            color: #f00;
        }
    `;
    document.head.appendChild(style);
    document.querySelectorAll(".image-placeholder").forEach(dropZone => {
        const fileInput = dropZone.querySelector("input");

        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.style.border = "2px solid blue";
        });

        dropZone.addEventListener("dragleave", () => {
            dropZone.style.border = "2px dashed #aaa";
        });

        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.style.border = "2px dashed #aaa";
            const file = e.dataTransfer.files[0];
            previewImage(file, dropZone);
        });

        fileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            previewImage(file, dropZone);
        });
    });

    function previewImage(file, dropZone) {
        if (file && file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = (e) => {
                dropZone.style.backgroundImage = `url(${e.target.result})`;
                dropZone.textContent = "";
                
                // Hide the input element but keep it functional
                const inputElement = dropZone.querySelector("input");
                if (inputElement) {
                    inputElement.style.display = "none";
                }
                
                // Add a reset button
                const resetBtn = document.createElement("button");
                resetBtn.className = "reset-image";
                resetBtn.textContent = "×";
                resetBtn.title = "Remove image";
                resetBtn.style.display = "none";
                
                // Show reset button on hover
                dropZone.addEventListener("mouseenter", () => {
                    resetBtn.style.display = "block";
                });
                
                dropZone.addEventListener("mouseleave", () => {
                    resetBtn.style.display = "none";
                });
                
                // Reset functionality
                resetBtn.addEventListener("click", (evt) => {
                    evt.stopPropagation();
                    dropZone.style.backgroundImage = "";
                    if (inputElement) {
                        inputElement.value = "";
                        inputElement.style.display = "block";
                    }
                    while (dropZone.firstChild) {
                        dropZone.removeChild(dropZone.firstChild);
                    }
                    
                    // Re-add the input element
                    dropZone.appendChild(inputElement);
                    
                    // Reset the text content
                    const textSpan = document.createElement("span");
                    textSpan.textContent = "Drag & Drop Image Here";
                    dropZone.appendChild(textSpan);
                    resetBtn.remove();
                });
                
                dropZone.appendChild(resetBtn);
            };
            reader.readAsDataURL(file);
        }
    }
});