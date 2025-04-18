// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AcademicCredentialVerification {
    address public admin;

    struct Student {
        string name;
        uint256 rollNumber;
        string branch;
        string email;
        string degree;
        bool isRegistered;
        string[] marksheetIPFS; // ✅ Changed from single string to array of strings
    }

    mapping(address => Student) public students;
    address[] public studentAddresses;

    event AdminAssigned(address indexed admin);
    event StudentRegistered(address indexed studentAddress, string name, uint256 rollNumber);
    event MarksheetIssued(address indexed studentAddress, string name, string marksheetIPFS);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }

    constructor(address _admin) {
        require(_admin != address(0), "Invalid admin address");
        admin = _admin;
        emit AdminAssigned(admin);
    }

   function registerStudent(
    address _studentAddress,
    string memory _name,
    uint256 _rollNumber,
    string memory _branch,
    string memory _email,
    string memory _degree
) public onlyAdmin {
    require(_studentAddress != address(0), "Invalid student address");
    require(!students[_studentAddress].isRegistered, "Student already registered");

    students[_studentAddress] = Student({
        name: _name,
        rollNumber: _rollNumber,
        branch: _branch,
        email: _email,
        degree: _degree,
        isRegistered: true,
        marksheetIPFS: new string[](0)   // ✅ Proper initialization
    });

    studentAddresses.push(_studentAddress);

    emit StudentRegistered(_studentAddress, _name, _rollNumber);
}


    function issueMarksheet(
        address _studentAddress,
        string memory _marksheetIPFS
    ) public onlyAdmin {
        require(students[_studentAddress].isRegistered, "Student not found");
        require(bytes(_marksheetIPFS).length > 0, "Invalid IPFS hash");

        students[_studentAddress].marksheetIPFS.push(_marksheetIPFS); // ✅ Push to array

        emit MarksheetIssued(_studentAddress, students[_studentAddress].name, _marksheetIPFS);
    }

    function getStudentDetails(address _studentAddress) public view returns (
        string memory name,
        uint256 rollNumber,
        string memory branch,
        string memory email,
        string memory degree,
        string[] memory marksheets
    ) {
        require(students[_studentAddress].isRegistered, "Student not found");

        Student memory s = students[_studentAddress];
        return (s.name, s.rollNumber, s.branch, s.email, s.degree, s.marksheetIPFS); // ✅ Now returns array
    }

    function getAllStudents() public view returns (address[] memory) {
        return studentAddresses;
    }
}