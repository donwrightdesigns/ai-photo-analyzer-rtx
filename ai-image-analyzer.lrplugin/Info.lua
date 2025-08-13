return {
	LrSdkVersion = 10.0,
	LrSdkMinimumVersion = 6.0,
	
	LrToolkitIdentifier = 'com.aiimageanalyzer.v2.lrplugin',
	LrPluginName = "AI Image Analyzer v2.0",
	
	LrPluginInfoUrl = "https://github.com/your-repo/ai-image-analyzer",
	
	LrLibraryMenuItems = {
		{
			title = "Analyze Selected Images",
			file = "AnalyzeImages.lua",
		},
		{
			title = "Batch Analyze Folder",
			file = "BatchAnalyze.lua",
		},
		{
			title = "View AI Analysis",
			file = "ViewAnalysis.lua",
		},
		{
			title = "Export Analysis Report",
			file = "ExportReport.lua",
		},
		{
			title = "Download Local Models", -- NEW FEATURE
			file = "DownloadModels.lua",
		},
		{
			title = "System Status", -- NEW FEATURE  
			file = "SystemStatus.lua",
		},
		{
			title = "Plugin Settings",
			file = "Settings.lua",
		}
	},
	
	LrMetadataProvider = "AIImageAnalyzerMetadataProvider.lua",
	
	VERSION = {
		major = 2,
		minor = 0,
		revision = 0,
		build = 1,
	},
}
