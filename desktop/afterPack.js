const path = require("path");
const rcedit = require("rcedit");

exports.default = async function (context) {
  if (context.electronPlatformName !== "win32") return;

  const exePath = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.exe`);
  const icoPath = path.join(__dirname, "assets", "icon.ico");

  await rcedit(exePath, { icon: icoPath });
};
