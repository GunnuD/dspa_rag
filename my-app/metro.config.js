const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Exclude electron folder from being bundled by Metro
config.resolver.sourceExts = [...config.resolver.sourceExts];
config.resolver.assetExts = [...config.resolver.assetExts];
config.resolver.blockList = [
  /electron\/.*/,
];

module.exports = config;
