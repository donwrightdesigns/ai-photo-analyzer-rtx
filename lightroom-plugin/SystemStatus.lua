local LrBinding = import 'LrBinding'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrHttp = import 'LrHttp'
local LrPrefs = import 'LrPrefs'
local LrView = import 'LrView'
local JSON = require 'JSON'

local prefs = LrPrefs.prefsForPlugin()

local function getApiUrl()
    return prefs.apiUrl or "http://localhost:5000"
end

local function checkSystemStatus()
    local status = {
        webService = false,
        ollama = false,
        models = {},
        version = "Unknown",
        error = nil
    }
    
    -- Check web service
    local response, headers = LrHttp.get(getApiUrl() .. "/api/model_status", {}, 10)
    
    if headers and headers.status == 200 then
        local result = JSON:decode(response)
        status.webService = true
        status.ollama = result.ollama_running or false
        status.models = result.models or {}
    else
        status.error = "Cannot connect to web service at " .. getApiUrl()
    end
    
    return status
end

-- Main function
LrFunctionContext.callWithContext("systemStatus", function(context)
    local viewFactory = LrView.osFactory()
    
    -- Get system status
    local systemStatus = checkSystemStatus()
    
    -- Create status text
    local statusText = ""
    
    -- Web Service Status
    if systemStatus.webService then
        statusText = statusText .. "✅ Web Service: Running\n"
        statusText = statusText .. "   URL: " .. getApiUrl() .. "\n\n"
    else
        statusText = statusText .. "❌ Web Service: Not Running\n"
        statusText = statusText .. "   URL: " .. getApiUrl() .. "\n"
        if systemStatus.error then
            statusText = statusText .. "   Error: " .. systemStatus.error .. "\n"
        end
        statusText = statusText .. "\n"
    end
    
    -- Ollama Status
    if systemStatus.ollama then
        statusText = statusText .. "✅ Ollama (Local AI): Running\n\n"
    else
        statusText = statusText .. "❌ Ollama (Local AI): Not Running\n"
        statusText = statusText .. "   Install from: https://ollama.ai\n\n"
    end
    
    -- Models Status
    statusText = statusText .. "📦 Available Models:\n"
    if #systemStatus.models > 0 then
        for _, model in ipairs(systemStatus.models) do
            statusText = statusText .. "   • " .. model .. "\n"
        end
    else
        statusText = statusText .. "   • No models installed\n"
        statusText = statusText .. "   • Use 'Download Local Models' to install\n"
    end
    statusText = statusText .. "\n"
    
    -- Plugin Configuration
    statusText = statusText .. "⚙️ Plugin Configuration:\n"
    statusText = statusText .. "   • Model Type: " .. (prefs.modelType or "local") .. "\n"
    statusText = statusText .. "   • EXIF Writing: " .. (prefs.writeExif and "Enabled" or "Disabled") .. "\n"
    statusText = statusText .. "   • Timeout: " .. (prefs.timeout or 120) .. " seconds\n"
    if prefs.apiKey and prefs.apiKey ~= "" then
        statusText = statusText .. "   • Google API Key: Configured\n"
    else
        statusText = statusText .. "   • Google API Key: Not Set\n"
    end
    statusText = statusText .. "\n"
    
    -- Recommendations
    statusText = statusText .. "💡 Recommendations:\n"
    
    if not systemStatus.webService then
        statusText = statusText .. "   • Start the web service: python web/app.py\n"
    end
    
    if not systemStatus.ollama and prefs.modelType == "local" then
        statusText = statusText .. "   • Install and start Ollama for local models\n"
    end
    
    if #systemStatus.models == 0 and systemStatus.ollama then
        statusText = statusText .. "   • Download a model using 'Download Local Models'\n"
    end
    
    if prefs.modelType == "cloud" and (not prefs.apiKey or prefs.apiKey == "") then
        statusText = statusText .. "   • Set Google API Key in Plugin Settings\n"
    end
    
    if systemStatus.webService and systemStatus.ollama and #systemStatus.models > 0 then
        statusText = statusText .. "   • System is ready for AI image analysis! ✨\n"
    end
    
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Image Analyzer System Status",
                font = "<system/bold>",
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:scrolled_view {
                width = 500,
                height = 400,
                viewFactory:column {
                    viewFactory:static_text {
                        title = statusText,
                        width_in_chars = 70,
                        height_in_lines = 30,
                    },
                },
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Refresh this dialog to update status information.",
                width_in_chars = 50,
            },
        },
    }
    
    local result = LrDialogs.presentModalDialog {
        title = "System Status - AI Image Analyzer v2.0",
        contents = contents,
        actionVerb = "OK",
    }
end)
