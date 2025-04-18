const hre = require("hardhat");

async function main() {
  const [admin] = await hre.ethers.getSigners();

  const AcademicCredential = await hre.ethers.getContractFactory("AcademicCredentialVerification");

  const contract = await AcademicCredential.deploy(admin.address);

  await contract.waitForDeployment(); // ✅ Replace .deployed() with .waitForDeployment()

  console.log(`✅ Contract deployed at: ${await contract.getAddress()}`);
  console.log(`👨‍💼 Admin address: ${admin.address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
