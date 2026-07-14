<script>
document.addEventListener('DOMContentLoaded', () => {
    // --- 1. JSON Data Constant ---
    const FILTER_DATA = {
        "Cancer type": {
            "ICD-O topography": {
                "C00-C14 Lip, oral cavity and pharynx": {
                    "C00 Lip": [
                        "C00.0 External upper lip",
                        "C00.1 External lower lip"
                    ],
                    "C01 Base of tongue": [
                        "C01.9 Base of tongue, nos"
                    ]
                }
            },
            "ICD-O histology": {
                "800 Neoplasms, NOS": ["include all", "8000/0 Neoplasm, benign"],
                "801-804 Epithelial neoplasms, NOS": ["include all", "8010/0 Epithelial tumor, benign"]
            },
            "CRUK terms": ["include all", "All"]
        },
        "Accessibility": ["Access restricted at present", "Open to applicants"],
        "Data": {
            "Biobank Samples": {
                "Material type": ["include all", "Bloods ", "Cells - eg cell lines"],
                "State": ["Malignant", "Normal", "Pre-cancerous"]
            },
            "In Vitro Study": {
                "include all": [],
                "Model": [
                    "include all",
                    "Organ on a Chip",
                    "3D organoid (including on a chip)",
                    "Organ slice"
                ]
            }
        }
    };

    // --- 2. Element References ---
    const topographyTreeContainer = document.getElementById('topography-tree');
    const histologyListContainer = document.getElementById('histology-list');
    const topoSearchInput = document.querySelector('.tree-search');
    const histoSearcInput = document.querySelector('.histology-search');


    // --- 3. Dynamic Tree Builder (Topography) ---

    const buildTreeHTML = (node, parentKey = '') => {
        let html = '';

        if (Array.isArray(node)) {
            // Final leaf nodes
            html += '<div class="final-options">';
            node.forEach((item, index) => {
                const id = `${parentKey}-${index}`.replace(/[^a-zA-Z0-9-]/g, '');
                html += `<div><input type="checkbox" id="${id}"><label for="${id}">${item}</label></div>`;
            });
            html += '</div>';
        } else if (typeof node === 'object' && node !== null) {
            // Internal nodes
            for (const key in node) {
                if (node.hasOwnProperty(key)) {
                    const uniqueKey = key.replace(/[^a-zA-Z0-9-]/g, '');
                    const currentId = `${parentKey ? parentKey + '-' : ''}${uniqueKey}`;

                    html += `<details>`;
                    html += `<summary><input type="checkbox" id="check-${currentId}"><label for="check-${currentId}">${key}</label></summary>`;

                    html += `<div class="nested-options" data-key="${uniqueKey}">`;
                    html += buildTreeHTML(node[key], currentId);
                    html += `</div>`;

                    html += `</details>`;
                }
            }
        }
        return html;
    };

    // --- 4. Dynamic List Builder (Histology) ---

    const buildListHTML = (histologyData) => {
        let html = '';

        // Flatten the histology data structure for list presentation
        const options = [];
        for (const group in histologyData) {
            if (histologyData.hasOwnProperty(group)) {
                histologyData[group].forEach(item => options.push({ group: group, item: item }));
            }
        }

        options.forEach((opt, index) => {
            const id = `histo-${index}`.replace(/[^a-zA-Z0-9-]/g, '');
            html += `<div class="list-item" data-group="${opt.group.toLowerCase()}">
                        <input type="checkbox" id="${id}">
                        <label for="${id}">${opt.item} (${opt.group.split(' ')[0]})</label>
                    </div>`;
        });

        return html;
    };


    // --- 5. Initialization ---
    const topoData = FILTER_DATA["Cancer type"]["ICD-O topography"];
    const histoData = FILTER_DATA["Cancer type"]["ICD-O histology"];

    if (topoData) {
        topographyTreeContainer.innerHTML = buildTreeHTML(topoData);
    }

    if (histoData) {
        histologyListContainer.innerHTML = buildListHTML(histoData);
    }


    // --- 6. Topography Search Logic (adapted for dynamic content) ---
    const filterTree = () => {
        const searchText = topoSearchInput.value.toLowerCase();
        const allLabels = topographyTreeContainer.querySelectorAll('label');

        allLabels.forEach(label => {
            const listItem = label.closest('details') || label.closest('.nested-options') || label.closest('.final-options > div');

            if (label.textContent.toLowerCase().includes(searchText)) {
                if (listItem) listItem.style.display = '';

                // Open all parent <details> elements
                let parentDetails = label.closest('details');
                while (parentDetails) {
                    parentDetails.open = true;
                    parentDetails = parentDetails.parentElement.closest('details');
                }
            } else {
                if (listItem) listItem.style.display = 'none';
            }
        });

        // Second pass: hide top-level sections that are now empty
        topographyTreeContainer.querySelectorAll('details').forEach(topDetails => {
            const visibleChildren = topDetails.querySelectorAll('.nested-options, .final-options');
            // Check if any child item is still visible (excluding the summary label)
            const hasVisibleChild = Array.from(visibleChildren).some(child =>
                Array.from(child.querySelectorAll('div, details')).some(item => item.style.display !== 'none')
            );

            if (!hasVisibleChild && searchText.length > 0) {
                topDetails.style.display = 'none';
            } else {
                topDetails.style.display = '';
            }
        });
    };

    topoSearchInput.addEventListener('input', filterTree);

    // --- 7. Histology Search Logic ---
    const filterList = () => {
        const searchText = histoSearcInput.value.toLowerCase();
        const allListItems = histologyListContainer.querySelectorAll('.list-item');

        allListItems.forEach(item => {
            const labelText = item.querySelector('label').textContent.toLowerCase();
            if (labelText.includes(searchText)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    };

    histoSearcInput.addEventListener('input', filterList);

});
</script>