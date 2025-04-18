// scripts/export-abi.js
const fs = require("fs");
const path = require("path");

async function main() {
  const artifact = await hre.artifacts.readArtifact("AcademicCredentialVerification");
  fs.writeFileSync(path.join(__dirname, "../abi/contract_abi.json"), JSON.stringify(artifact.abi, null, 2));
  console.log("✅ ABI exported to abi/contract_abi.json");
}

main();
