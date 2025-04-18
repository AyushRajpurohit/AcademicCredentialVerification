import gradio as gr
from web3 import Web3
import json
import os
import requests
from dotenv import load_dotenv
import webbrowser

load_dotenv()

# Load env vars
w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_PROVIDER")))
private_key = os.getenv("PRIVATE_KEY")
admin_address = os.getenv("ADMIN_ADDRESS")
contract_address = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))

ipfs_hash_list = []

# Load ABI
with open('contracts/AcademicCredentialVerification.abi.json') as f:
    abi = json.load(f)

contract = w3.eth.contract(address=contract_address, abi=abi)

# Helper: Upload to IPFS via Pinata
def upload_to_ipfs(file_path):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": os.getenv("PINATA_API_KEY"),
        "pinata_secret_api_key": os.getenv("PINATA_SECRET")
    }
    with open(file_path, "rb") as f:
        files = {'file': f}
        response = requests.post(url, files=files, headers=headers)
        if response.status_code == 200:
            return response.json()['IpfsHash']
        else:
            return None



# Register student
def register_student(address, name, roll, branch, email, degree):
    try:
        
        tx = contract.functions.registerStudent(
            Web3.to_checksum_address(address),
            name,
            int(roll),
            branch,
            email,
            degree
        ).build_transaction({
            'from': Web3.to_checksum_address(admin_address),
            'gas': 300000,
            'nonce': w3.eth.get_transaction_count(Web3.to_checksum_address(admin_address)),
            "gasPrice": w3.eth.gas_price,
        })
        signed_txn = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # ✅ this is correct

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return f"Student Registered. Tx Hash: {tx_hash.hex()}"
    except Exception as e:
        return f"Error: {str(e)}"
    


def student_details(student_addr):
    try:
        details = contract.functions.getStudentDetails(Web3.to_checksum_address(student_addr)).call()
        marksheet_list = details[5]  # List of IPFS hashes
        file_name = []
        file_name = get_filename(marksheet_list)
        print("\nfile_name\n",file_name,"\n")

        # Generate download links with actual filenames
        if marksheet_list:
            download_links = [
                f'<a href="https://ipfs.io/ipfs/{ipfs}" target="_blank" download>{file}</a>'
                for ipfs, file in zip(marksheet_list, file_name)
            ]
            ipfs_output_html = "<br>".join(download_links)
        else:
            ipfs_output_html = "No marksheets issued yet."

        info_output = f"""
        Name: {details[0]}<br>
        Roll No: {details[1]}<br>
        Branch: {details[2]}<br>
        Email: {details[3]}<br>
        Degree: {details[4]}<br><br>
        Marksheet Downloads:<br>{ipfs_output_html}
        """
        return info_output

    except Exception as e:
        return f"❌ Error: {str(e)}"


def get_filename(ipfs_cid):
    print(ipfs_cid)
    url = "https://api.pinata.cloud/data/pinList"
    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": os.getenv("PINATA_API_KEY"),
        "pinata_secret_api_key": os.getenv("PINATA_SECRET"),
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        file_names = filter_file_names_from_response(data, ipfs_cid)
        print("\nfile_name",file_names,"\n")
        return file_names

    except requests.exceptions.RequestException as e:
        print(f"Error during Pinata API request: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Pinata API.")
        return None

def filter_file_names_from_response(server_response, ipfs_list):
    # Extract rows from server response
    rows = server_response.get('rows', [])
    
    # Create a mapping of ipfs_hash -> file name
    ipfs_to_name = {
        row['ipfs_pin_hash']: row['metadata']['name']
        for row in rows if 'metadata' in row and row['metadata'] and 'name' in row['metadata']
    }
    
    # Return list of file names that match the IPFS codes in ipfs_list
    return [ipfs_to_name[ipfs] for ipfs in ipfs_list if ipfs in ipfs_to_name]


def get_filename_from_ipfs(ipfs_hash):
        try:
            ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
            response = requests.head(ipfs_url, allow_redirects=True, timeout=50)
            print(response)
            # First try Content-Disposition header
            content_disp = response.headers.get('Content-Disposition')
            print("conetent_disp")
            print(content_disp)
            if content_disp and 'filename=' in content_disp:
                filename = content_disp.split('filename=')[-1].strip('"')
                return filename
            print("below")
            # Fallback: use the last part of the URL if redirect adds filename
            redirected_url = response.url
            print("above")
            if redirected_url != ipfs_url:
                print("inside")
                return os.path.basename(redirected_url)
        
            # Fallback again: just use IPFS hash
            return f"{ipfs_hash[:8]}... (Unknown File)"
   
        except Exception as e:
            print(f"⚠️ Could not fetch filename for {ipfs_hash}: {e}")
            return f"{ipfs_hash[:8]}... (Unknown File)"

    


def display_student_info(student_addr): 
    details, ipfs_list = student_details(student_addr)
    # If error string is returned
    if isinstance(details, str):
        return details, ""

    # Format details as Markdown
    info = "\n".join([f"**{key}:** {value}" for key, value in details.items()])

    # Format links for download
    if ipfs_list:
        links_html = "<br>".join([
            f'<a href="https://gateway.pinata.cloud/ipfs/{ipfs}" target="_blank" download>Download Marksheet {i+1}</a>'
            for i, ipfs in enumerate(ipfs_list)
        ])
    else:
        links_html = "No marksheets issued yet."

    return info, links_html




# Issue marksheet
def issue_certificate(address, file):
    ipfs_hash = upload_to_ipfs(file.name)
    ipfs_hash_list.append(ipfs_hash)
    print(ipfs_hash_list)
    if not ipfs_hash:
        return "IPFS upload failed."
    try:
        nonce = w3.eth.get_transaction_count(admin_address)
        tx = contract.functions.issueMarksheet(
            Web3.to_checksum_address(address),
            ipfs_hash
        ).build_transaction({
            'from': admin_address,
            'gas': 300000,
            'nonce': nonce
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return f"Certificate Issued. IPFS: {ipfs_hash}\nTx Hash: {tx_hash.hex()}"
    except Exception as e:
        return f"Error: {str(e)}"

# Verify certificate
def verify_certificate(address, uploaded_file):
    try:
        stored_hash = contract.functions.getStudentDetails(Web3.to_checksum_address(address)).call()[5]
        uploaded_ipfs_hash = upload_to_ipfs(uploaded_file.name)
        if uploaded_ipfs_hash in stored_hash:
            return f"✅ Valid certificate. IPFS: {uploaded_ipfs_hash}"
        else:
            return f"❌ Invalid certificate. Uploaded IPFS: {uploaded_ipfs_hash}, Stored IPFS: {stored_hash}"
    except Exception as e:
        return f"Error: {str(e)}"

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## 🎓 Academic Credential Verification - Blockchain + IPFS")

    with gr.Tab("Register Student"):
        addr = gr.Textbox(label="Student Wallet Address")
        name = gr.Textbox(label="Name")
        roll = gr.Textbox(label="Roll Number")
        branch = gr.Textbox(label="Branch")
        email = gr.Textbox(label="Email")
        degree = gr.Textbox(label="Degree")
        out1 = gr.Textbox(label="Status")
        btn1 = gr.Button("Register")
        btn1.click(register_student, inputs=[addr, name, roll, branch, email, degree], outputs=out1)


    with gr.Tab("Student Details"):
        student_address_input = gr.Textbox(label="Enter Student Address")
        student_details_output = gr.HTML()

        get_details_btn = gr.Button("Get Student Details")
        get_details_btn.click(fn=student_details, inputs=[student_address_input], outputs=[student_details_output])

    with gr.Tab("Issue Certificate"):
        addr3 = gr.Textbox(label="Student Wallet Address")
        file = gr.File(label="Upload Marksheet PDF", file_types=[".pdf"])
        out3 = gr.Textbox(label="Status")
        btn3 = gr.Button("Issue Marksheet")
        btn3.click(issue_certificate, inputs=[addr3, file], outputs=out3)

    with gr.Tab("Verify Certificate"):
        addr4 = gr.Textbox(label="Student Wallet Address")
        file2 = gr.File(label="Upload Certificate PDF", file_types=[".pdf"])
        out4 = gr.Textbox(label="Verification Result")
        btn4 = gr.Button("Verify")
        btn4.click(verify_certificate, inputs=[addr4, file2], outputs=out4)

demo.launch()
