local LrBinding = import 'LrBinding'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrPrefs = import 'LrPrefs'
local LrView = import 'LrView'

local prefs = LrPrefs.prefsForPlugin()

LrFunctionContext.callWithContext("AI Image Analyzer Settings", function(context)
    local viewFactory = LrView.osFactory()
local properties = LrBinding.makePropertyTable(context)
    
    -- Initialize properties with current preferences
    properties.apiUrl = prefs.apiUrl or "http://localhost:5000"
    properties.writeExif = prefs.writeExif or true
    properties.timeout = prefs.timeout or 120
    properties.modelType = prefs.modelType or "llava"
    properties.enableGalleryCritique = prefs.enableGalleryCritique or false
    properties.generateXmp = prefs.generateXmp or false
    properties.critiqueThreshold = prefs.critiqueThreshold or 5
    properties.apiKey = prefs.apiKey or ""
    
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Model Type:",
                width = 120,
            },
            viewFactory:popup_menu {
                value = LrBinding.bind("modelType"),
                items = {
                    { title = "LLaVA (Ollama)", value = "llava" },
                    { title = "Gemini (Cloud)", value = "gemini" },
                },
            },
        },

        viewFactory:row {
            viewFactory:static_text {
                title = "API Key:",
                width = 120,
            },
            viewFactory:edit_field {
                value = LrBinding.bind("apiKey"),
                password = true,
                width_in_chars = 40,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Service URL:",
                width = 120,
            },
            
            viewFactory:edit_field {
                value = LrBinding.bind("apiUrl"),
                width_in_chars = 40,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Request Timeout (seconds):",
                width = 120,
            },
            
            viewFactory:edit_field {
                value = LrBinding.bind("timeout"),
                width_in_chars = 10,
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Write analysis to EXIF metadata",
                value = LrBinding.bind("writeExif"),
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Generate XMP sidecar files",
                value = LrBinding.bind("generateXmp"),
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Enable gallery critique for all images",
                value = LrBinding.bind("enableGalleryCritique"),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Critique threshold (1-10):",
                width = 120,
            },
            
            viewFactory:edit_field {
                value = LrBinding.bind("critiqueThreshold"),
                width_in_chars = 5,
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Plugin Information:",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Image Analyzer for Adobe Lightroom",
                width_in_chars = 50,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Integrates with the AI Image Analyzer Flask web service",
                width_in_chars = 50,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Uses LLaVA and Gemini AI models with XMP support",
                width_in_chars = 50,
            },
        },
    }
    
    local result = LrDialogs.presentModalDialog {
        title = "AI Image Analyzer Settings",
        contents = contents,
        actionVerb = "Save",
    }
    
    if result == "ok" then
        prefs.apiUrl = properties.apiUrl
        prefs.writeExif = properties.writeExif
        prefs.timeout = tonumber(properties.timeout) or 120
        prefs.modelType = properties.modelType
        prefs.apiKey = properties.apiKey
        prefs.enableGalleryCritique = properties.enableGalleryCritique
        prefs.generateXmp = properties.generateXmp
        prefs.critiqueThreshold = tonumber(properties.critiqueThreshold) or 5
        
        LrDialogs.message("Settings Saved", "AI Image Analyzer settings have been saved successfully.")
    end
end)
