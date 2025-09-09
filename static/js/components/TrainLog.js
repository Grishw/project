function appendTrainLog(line){
    const host = document.getElementById('train_log');
    if (!host) return;
    const ts = new Date().toLocaleTimeString();
    host.textContent += `[${ts}] ${line}\n`;
}

export default appendTrainLog;