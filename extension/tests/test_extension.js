// Test script for Job Application Assistant extension

// Function to simulate extension popup actions
async function testExtension() {
    console.log('Starting extension tests...');

    // Test 1: Form Detection
    console.log('\nTest 1: Form Detection');
    try {
        const hasForm = await chrome.runtime.sendMessage({action: "checkForm"});
        console.log('Form detection result:', hasForm);
        if (!hasForm.hasForm) {
            throw new Error('Form detection failed');
        }
        console.log('✓ Form detection passed');
    } catch (error) {
        console.error('✗ Form detection failed:', error);
    }

    // Test 2: Form Analysis
    console.log('\nTest 2: Form Analysis');
    try {
        const analysis = await chrome.runtime.sendMessage({action: "analyzeForm"});
        console.log('Form analysis result:', analysis);
        if (!analysis.success) {
            throw new Error('Form analysis failed');
        }
        console.log('✓ Form analysis passed');
    } catch (error) {
        console.error('✗ Form analysis failed:', error);
    }

    // Test 3: Form Filling
    console.log('\nTest 3: Form Filling');
    try {
        const fillResult = await chrome.runtime.sendMessage({action: "fillForm"});
        console.log('Form filling result:', fillResult);
        if (!fillResult.success) {
            throw new Error('Form filling failed');
        }
        console.log('✓ Form filling passed');
    } catch (error) {
        console.error('✗ Form filling failed:', error);
    }

    // Test 4: Field Validation
    console.log('\nTest 4: Field Validation');
    try {
        const form = document.getElementById('application-form');
        const fields = form.elements;
        let allFieldsFilled = true;

        for (let field of fields) {
            if (field.required && !field.value) {
                allFieldsFilled = false;
                console.error(`Field ${field.id} is empty`);
            }
        }

        if (!allFieldsFilled) {
            throw new Error('Some required fields are empty');
        }
        console.log('✓ Field validation passed');
    } catch (error) {
        console.error('✗ Field validation failed:', error);
    }

    // Test 5: Job Description Extraction
    console.log('\nTest 5: Job Description Extraction');
    try {
        const jobDesc = document.getElementById('job-description').textContent;
        if (!jobDesc || jobDesc.length < 100) {
            throw new Error('Job description extraction failed');
        }
        console.log('✓ Job description extraction passed');
    } catch (error) {
        console.error('✗ Job description extraction failed:', error);
    }
}

// Run tests when the page is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Test page loaded, starting tests...');
    testExtension();
}); 