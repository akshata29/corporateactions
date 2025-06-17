# Inquiry Creation UI Integration Guide

## Overview
The enhanced inquiry creation system supports popup workflows for better user experience.

## How It Works

### 1. Triggering the Popup
When a user clicks "Create Inquiry", call the `create_inquiry_with_ui_tool`:

```javascript
// Example client-side JavaScript
async function createInquiry(eventId, userId, userName, organization) {
    const response = await callMCPTool('create_inquiry_with_ui_tool', {
        event_id: eventId,
        user_id: userId,
        user_name: userName,
        organization: organization,
        show_popup: true
    });
    
    const result = JSON.parse(response);
    if (result.action === 'show_inquiry_popup') {
        showInquiryPopup(result);
    }
}
```

### 2. Popup Configuration
The tool returns a configuration object like this:

```json
{
    "action": "show_inquiry_popup",
    "event_id": "AAPL_DIV_2024_Q1",
    "user_id": "user123",
    "user_name": "John Doe",
    "organization": "ABC Corp",
    "popup_config": {
        "title": "Create Inquiry for Event AAPL_DIV_2024_Q1",
        "fields": [
            {
                "name": "subject",
                "label": "Subject",
                "type": "text",
                "required": true,
                "placeholder": "Brief description of your inquiry"
            },
            {
                "name": "description",
                "label": "Description", 
                "type": "textarea",
                "required": true,
                "placeholder": "Provide detailed information about your inquiry",
                "rows": 4
            },
            {
                "name": "priority",
                "label": "Priority",
                "type": "select",
                "required": true,
                "options": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                "default": "MEDIUM"
            }
        ],
        "submit_endpoint": "submit_inquiry_tool",
        "cancel_text": "Cancel",
        "submit_text": "Create Inquiry"
    }
}
```

### 3. Displaying the Popup
Create a popup/modal with the specified fields:

```javascript
function showInquiryPopup(config) {
    const modal = document.createElement('div');
    modal.className = 'inquiry-modal';
    
    // Create form based on config.popup_config.fields
    const form = createForm(config.popup_config.fields);
    
    // Handle form submission
    form.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        
        await submitInquiry(config, formData);
    };
    
    modal.appendChild(form);
    document.body.appendChild(modal);
}
```

### 4. Submitting the Inquiry
When the user submits the form, call `submit_inquiry_tool`:

```javascript
async function submitInquiry(config, formData) {
    const response = await callMCPTool('submit_inquiry_tool', {
        event_id: config.event_id,
        user_id: config.user_id,
        user_name: config.user_name,
        organization: config.organization,
        subject: formData.get('subject'),
        description: formData.get('description'),
        priority: formData.get('priority')
    });
    
    const result = JSON.parse(response);
    
    if (result.success) {
        showSuccessMessage(result.popup_response);
        closePopup();
        refreshInquiriesList();
    } else {
        showErrorMessage(result.popup_response);
    }
}
```

### 5. Response Handling
The submit tool returns structured responses:

**Success Response:**
```json
{
    "action": "inquiry_created",
    "success": true,
    "inquiry_id": "INQ_AAPL_DIV_2024_Q1_20240616_143045",
    "message": "Inquiry created successfully for AAPL_DIV_2024_Q1",
    "popup_response": {
        "type": "success",
        "title": "Inquiry Created Successfully",
        "message": "Your inquiry has been created with ID: INQ_AAPL_DIV_2024_Q1_20240616_143045",
        "auto_close": 3000
    }
}
```

**Error Response:**
```json
{
    "action": "inquiry_failed",
    "success": false,
    "error": "Database connection not available",
    "popup_response": {
        "type": "error",
        "title": "Failed to Create Inquiry",
        "message": "Error: Database connection not available",
        "auto_close": 5000
    }
}
```

## Sample Data Generation

Use `generate_sample_data_tool` to create sample corporate actions and related inquiries:

```javascript
async function generateSampleData() {
    const response = await callMCPTool('generate_sample_data_tool', {
        symbols: 'AAPL,MSFT,TSLA,GOOGL,AMZN',
        num_events_per_symbol: 3
    });
    
    const result = JSON.parse(response);
    console.log(`Generated ${result.summary.total_events} events and ${result.summary.total_inquiries} inquiries`);
}
```

## Debugging

Use `debug_inquiry_creation_tool` to diagnose issues:

```javascript
async function debugInquiryCreation(eventId) {
    const response = await callMCPTool('debug_inquiry_creation_tool', {
        event_id: eventId
    });
    
    const result = JSON.parse(response);
    console.log('Debug info:', result.debug_info);
}
```

## CSS Example for Popup

```css
.inquiry-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.inquiry-form {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

.inquiry-field {
    margin-bottom: 1rem;
}

.inquiry-field label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
}

.inquiry-field input,
.inquiry-field textarea,
.inquiry-field select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}

.inquiry-buttons {
    display: flex;
    gap: 1rem;
    justify-content: flex-end;
    margin-top: 1rem;
}

.btn-primary {
    background: #007bff;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-secondary {
    background: #6c757d;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
}
```
