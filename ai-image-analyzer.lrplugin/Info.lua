return {
	LrSdkVersion = 10.0,
	LrSdkMinimumVersion = 6.0,
	
	LrToolkitIdentifier = 'com.aiimageanalyzer.v2.lrplugin',
	LrPluginName = "AI Image Analyzer v2.1 - Multi-Stage Pipeline",
	
	LrPluginInfoUrl = "https://github.com/your-repo/ai-image-analyzer",
	
	LrLibraryMenuItems = {
		{
			title = "🚀 Multi-Stage Analysis (IQA + AI)", -- NEW: Advanced pipeline
			file = "MultiStageAnalysis.lua",
		},
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
			title = "Download Local Models",
			file = "DownloadModels.lua",
		},
		{
			title = "System Status",
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
