local LrTasks = import 'LrTasks'
local AIImageAnalyzer = require 'AIImageAnalyzerAPI'

LrTasks.startAsyncTask(function()
    AIImageAnalyzer.analyzeSelectedImages()
end)
