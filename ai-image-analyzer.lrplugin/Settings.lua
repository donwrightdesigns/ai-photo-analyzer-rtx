local LrBinding = import 'LrBinding'
local LrColor = import 'LrColor'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrPrefs = import 'LrPrefs'
local LrView = import 'LrView'

local prefs = LrPrefs.prefsForPlugin()

LrFunctionContext.callWithContext("AI Image Analyzer Settings", function(context)
    local viewFactory = LrView.osFactory()
    local properties = LrBinding.makePropertyTable(context)
    
    -- Initialize properties with current preferences
    properties.apiUrl = prefs.apiUrl or "http://localhost:5001"
    properties.writeExif = prefs.writeExif or true
    properties.timeout = prefs.timeout or 120
    properties.modelType = prefs.modelType or "gemini"
    properties.promptProfile = prefs.promptProfile or "professional_art_critic"
    properties.enableGalleryCritique = prefs.enableGalleryCritique or false
    properties.generateXmp = prefs.generateXmp or true
    properties.critiqueThreshold = prefs.critiqueThreshold or 5
    properties.apiKey = prefs.apiKey or ""
    -- Multi-stage pipeline settings
    properties.qualityThreshold = prefs.qualityThreshold or 0.10
    properties.iqaModel = prefs.iqaModel or "brisque"
    properties.useExif = prefs.useExif or false
    
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Model Type:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "modelType",
                items = {
                    { title = "Ollama (Local)", value = "ollama" },
                    { title = "Google Gemini (Cloud)", value = "gemini" },
                    { title = "BakLLaVA (Local)", value = "bakllava" },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Analysis Perspective:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "promptProfile",
                items = {
                    { title = "Professional Art Critic", value = "professional_art_critic" },
                    { title = "Family Memory Keeper", value = "family_archivist" },
                    { title = "Commercial Photographer", value = "commercial_photographer" },
                    { title = "Social Media Expert", value = "social_media_curator" },
                    { title = "Documentary Journalist", value = "documentary_journalist" },
                    { title = "Travel Content Creator", value = "travel_blogger" },
                },
            },
        },

        viewFactory:row {
            viewFactory:static_text {
                title = "API Key:",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "apiKey",
                password = true,
                width_in_chars = 40,
                enabled = LrBinding.keyEquals("modelType", "gemini", properties),
                tooltip = "Required only for Google Gemini (Cloud). Leave empty for local models.",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "💡 API Key is only required for Google Gemini. Local models (Ollama/BakLLaVA) don't need an API key.",
                width_in_chars = 60,
                height_in_lines = 2,
                text_color = LrColor('gray'),
                visible = LrBinding.keyEquals("modelType", "ollama", properties) or LrBinding.keyEquals("modelType", "bakllava", properties),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "🔑 Get your free API key at: https://aistudio.google.com/",
                width_in_chars = 60,
                text_color = LrColor('blue'),
                visible = LrBinding.keyEquals("modelType", "gemini", properties),
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
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Write analysis to EXIF metadata",
                bind_to_object = properties,
                value = "writeExif",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Generate XMP sidecar files",
                bind_to_object = properties,
                value = "generateXmp",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Enable gallery critique for all images",
                bind_to_object = properties,
                value = "enableGalleryCritique",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Critique threshold (1-10):",
                width = 120,
            },
            
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "critiqueThreshold",
                width_in_chars = 5,
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Multi-Stage Pipeline Settings
        viewFactory:row {
            viewFactory:static_text {
                title = "🚀 Multi-Stage Pipeline Settings:",
                font = "<system/bold>",
                text_color = LrColor('blue'),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "IQA Model:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "iqaModel",
                items = {
                    { title = "BRISQUE (Recommended)", value = "brisque" },
                    { title = "NIQE", value = "niqe" },
                    { title = "MUSIQ", value = "musiq" },
                    { title = "TOPIQ", value = "topiq" },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Quality Threshold:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "qualityThreshold",
                items = {
                    { title = "Top 5% (Ultra-selective)", value = 0.05 },
                    { title = "Top 10% (Recommended)", value = 0.10 },
                    { title = "Top 15% (Balanced)", value = 0.15 },
                    { title = "Top 20% (Liberal)", value = 0.20 },
                    { title = "Top 25% (Very Liberal)", value = 0.25 },
                    { title = "Top 50% (Remove worst only)", value = 0.50 },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Use EXIF for multi-stage (otherwise XMP sidecars)",
                bind_to_object = properties,
                value = "useExif",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "💡 Multi-stage pipeline: Quality Assessment → AI Analysis → Metadata\n" ..
                        "Saves 85% processing time and 90% API costs by filtering low-quality images",
                width_in_chars = 60,
                height_in_lines = 3,
                text_color = LrColor('gray'),
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
                title = "Supports Ollama, Gemini, and BakLLaVA models",
                width_in_chars = 50,
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Features XMP sidecar files and prompt profiles",
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
        prefs.promptProfile = properties.promptProfile
        prefs.apiKey = properties.apiKey
        prefs.enableGalleryCritique = properties.enableGalleryCritique
        prefs.generateXmp = properties.generateXmp
        prefs.critiqueThreshold = tonumber(properties.critiqueThreshold) or 5
        -- Save multi-stage pipeline settings
        prefs.qualityThreshold = properties.qualityThreshold
        prefs.iqaModel = properties.iqaModel
        prefs.useExif = properties.useExif
        
        LrDialogs.message("Settings Saved", "AI Image Analyzer settings have been saved successfully.")
    end
end)
