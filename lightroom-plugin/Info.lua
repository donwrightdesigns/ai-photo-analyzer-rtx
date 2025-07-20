return {
	LrSdkVersion = 10.0,
	LrSdkMinimumVersion = 6.0,
	
	LrToolkitIdentifier = 'com.aiimageanalyzer.lrplugin',
	LrPluginName = "AI Image Analyzer",
	
	LrPluginInfoUrl = "https://github.com/your-repo/ai-image-analyzer",
	LrPluginInfoProvider = "AIImageAnalyzerInfoProvider.lua",
	
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
			title = "Plugin Settings",
			file = "Settings.lua",
		}
	},
	
	LrMetadataProvider = "AIImageAnalyzerMetadataProvider.lua",
	
	VERSION = {
		major = 1,
		minor = 0,
		revision = 0,
		build = 1,
	},
}
