//! Runs one `python -m tools.<module> …` command on a worker thread (game version switch,
//! assembly edits). The panel polls it each frame and reads stdout / stderr when it is done.

use std::io::Write;
use std::path::Path;
use std::process::Stdio;
use std::sync::mpsc::{channel, Receiver, TryRecvError};

#[derive(Clone, Debug, Default)]
pub struct ToolResult {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
}

impl ToolResult {
    /// The most useful single line: the error when it failed, else the last stdout line.
    pub fn summary(&self) -> String {
        let pick = if self.ok { &self.stdout } else if self.stderr.trim().is_empty() { &self.stdout } else { &self.stderr };
        pick.lines().rev().find(|l| !l.trim().is_empty()).unwrap_or("").trim().to_string()
    }
}

#[derive(Default)]
pub struct ToolJob {
    rx: Option<Receiver<ToolResult>>,
    /// what is running, for the status line
    pub label: String,
    pub last: Option<ToolResult>,
}

impl ToolJob {
    pub fn running(&self) -> bool {
        self.rx.is_some()
    }

    /// Starts `python -m <module> <args>` in `root`, writing `stdin` to it when given.
    pub fn start(&mut self, root: &Path, label: &str, module: &str, args: Vec<String>, stdin: Option<String>) {
        if self.running() {
            return;
        }
        let (tx, rx) = channel();
        self.rx = Some(rx);
        self.label = label.to_string();
        self.last = None;
        let root = root.to_path_buf();
        let module = module.to_string();
        std::thread::spawn(move || {
            let child = std::process::Command::new("python")
                .arg("-m")
                .arg(&module)
                .args(&args)
                .current_dir(&root)
                .env("PYTHONIOENCODING", "utf-8")
                .stdin(if stdin.is_some() { Stdio::piped() } else { Stdio::null() })
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn();
            let result = match child {
                Ok(mut child) => {
                    if let (Some(text), Some(mut pipe)) = (stdin, child.stdin.take()) {
                        let _ = pipe.write_all(text.as_bytes());
                    }
                    match child.wait_with_output() {
                        Ok(out) => ToolResult {
                            ok: out.status.success(),
                            stdout: String::from_utf8_lossy(&out.stdout).into_owned(),
                            stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
                        },
                        Err(err) => ToolResult { ok: false, stdout: String::new(), stderr: err.to_string() },
                    }
                }
                Err(err) => ToolResult {
                    ok: false,
                    stdout: String::new(),
                    stderr: format!("could not run python ({err}); check that Python 3 is on PATH"),
                },
            };
            let _ = tx.send(result);
        });
    }

    /// Returns the result once, in the frame it arrives.
    pub fn poll(&mut self) -> Option<ToolResult> {
        let rx = self.rx.as_ref()?;
        match rx.try_recv() {
            Ok(result) => {
                self.rx = None;
                self.last = Some(result.clone());
                Some(result)
            }
            Err(TryRecvError::Empty) => None,
            Err(TryRecvError::Disconnected) => {
                self.rx = None;
                let result = ToolResult { ok: false, stdout: String::new(), stderr: "the tool stopped".into() };
                self.last = Some(result.clone());
                Some(result)
            }
        }
    }
}
