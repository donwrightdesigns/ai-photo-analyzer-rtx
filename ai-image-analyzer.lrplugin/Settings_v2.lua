local LrBinding = import 'LrBinding'
local LrColor = import 'LrColor'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrPrefs = import 'LrPrefs'
local LrView = import 'LrView'

local prefs = LrPrefs.prefsForPlugin()

LrFunctionContext.callWithContext("AI Image Analyzer v2.0 Settings", function(context)
    local viewFactory = LrView.osFactory()
    local properties = LrBinding.makePropertyTable(context)
    
    -- Initialize properties with current preferences
    properties.apiUrl = prefs.apiUrl or "http://localhost:5001"
    properties.writeExif = prefs.writeExif or true
    properties.timeout = prefs.timeout or 120
    properties.modelType = prefs.modelType or "local"
    properties.apiKey = prefs.apiKey or ""
    properties.optimizeImages = prefs.optimizeImages or true  -- NEW
    properties.maxWorkers = prefs.maxWorkers or 2  -- NEW
    properties.enableLogging = prefs.enableLogging or true  -- NEW
    properties.lightRoomIntegration = prefs.lightRoomIntegration or true  -- NEW
    
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        -- Header
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Image Analyzer v2.0 Settings",
                font = "<system/bold>",
                width_in_chars = 50,
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Model Configuration Section
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Model Configuration",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Model Type:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "modelType",
                items = {
                    { title = "Local (LLaVA via Ollama)", value = "local" },
                    { title = "Cloud (Google Gemini)", value = "cloud" },
                    { title = "Auto (Detect Available)", value = "auto" },  -- NEW
                },
            },
        },

        viewFactory:row {
            viewFactory:static_text {
                title = "Google API Key:",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "apiKey",
                password = true,
                width_in_chars = 40,
                enabled = LrBinding.keyEquals("modelType", "cloud", properties) or LrBinding.keyEquals("modelType", "auto", properties),
                tooltip = "Required only for Cloud and Auto modes. Leave empty for Local mode.",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "💡 API Key is only required for Cloud/Auto modes. Local models don't need an API key.",
                width_in_chars = 60,
                height_in_lines = 2,
                text_color = LrColor('gray'),
                visible = LrBinding.keyEquals("modelType", "local", properties),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "🔑 Get your free Google AI API key at: https://aistudio.google.com/",
                width_in_chars = 60,
                text_color = LrColor('blue'),
                visible = LrBinding.keyEquals("modelType", "cloud", properties) or LrBinding.keyEquals("modelType", "auto", properties),
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Connection Settings Section
        viewFactory:row {
            viewFactory:static_text {
                title = "Connection Settings",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Service URL:",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "apiUrl",
                width_in_chars = 40,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Request Timeout (seconds):",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "timeout",
                width_in_chars = 10,
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Performance Settings Section - NEW
        viewFactory:row {
            viewFactory:static_text {
                title = "Performance Settings",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Max Concurrent Workers:",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "maxWorkers",
                width_in_chars = 10,
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Optimize images for faster processing",
                bind_to_object = properties,
                value = "optimizeImages",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Enable Lightroom resource monitoring",
                bind_to_object = properties,
                value = "lightRoomIntegration",
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Output Settings Section
        viewFactory:row {
            viewFactory:static_text {
                title = "Output Settings",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Write analysis to EXIF metadata",
                bind_to_object = properties,
                value = "writeExif",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Enable detailed logging",
                bind_to_object = properties,
                value = "enableLogging",
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Information Section
        viewFactory:row {
            viewFactory:static_text {
                title = "Plugin Information",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• Supports both local (LLaVA) and cloud (Gemini) AI models",
                width_in_chars = 60,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• Enhanced with image optimization and system monitoring",
                width_in_chars = 60,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• Automatic Lightroom resource detection and throttling",
                width_in_chars = 60,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• Comprehensive logging and progress tracking",
                width_in_chars = 60,
            },
        },
    }
    
    local result = LrDialogs.presentModalDialog {
        title = "AI Image Analyzer v2.0 Settings",
        contents = contents,
        actionVerb = "Save",
    }
    
    if result == "ok" then
        prefs.apiUrl = properties.apiUrl
        prefs.writeExif = properties.writeExif
        prefs.timeout = tonumber(properties.timeout) or 120
        prefs.modelType = properties.modelType
        prefs.apiKey = properties.apiKey
        prefs.optimizeImages = properties.optimizeImages  -- NEW
        prefs.maxWorkers = tonumber(properties.maxWorkers) or 2  -- NEW
        prefs.enableLogging = properties.enableLogging  -- NEW
        prefs.lightRoomIntegration = properties.lightRoomIntegration  -- NEW
        
        LrDialogs.message("Settings Saved", "AI Image Analyzer v2.0 settings have been saved successfully.")
    end
end)
