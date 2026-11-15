use std::fs;
use std::io::{self, Write};
use std::process::ExitCode;

use wurl::{Method, Request, Url};

struct Options {
    url: String,
    method: Option<Method>,
    headers: Vec<(String, String)>,
    data: Option<String>,
    upload_file: Option<String>,
    output: Option<String>,
    remote_name: bool,
    show_headers: bool,
    head_only: bool,
    fail_on_error: bool,
    silent: bool,
    verbose: bool,
    user_agent: Option<String>,
    user: Option<String>,
}

fn main() -> ExitCode {
    let options = match parse_args() {
        Ok(options) => options,
        Err(message) => {
            eprintln!("wurl: {message}");
            return ExitCode::FAILURE;
        }
    };

    let url = match Url::parse(&options.url) {
        Ok(url) => url,
        Err(error) => {
            eprintln!("wurl: {error}");
            return ExitCode::FAILURE;
        }
    };

    let request = build_request(url, &options);

    if options.verbose {
        eprint_request(&request);
    }

    let response = match wurl::send(&request) {
        Ok(response) => response,
        Err(error) => {
            if !options.silent {
                eprintln!("wurl: {error}");
            }
            return ExitCode::FAILURE;
        }
    };

    if options.fail_on_error && response.status >= 400 {
        if !options.silent {
            eprintln!(
                "wurl: HTTP error {} for {}",
                response.status, options.url
            );
        }
        return ExitCode::FAILURE;
    }

    if options.verbose {
        eprint!("{}", response.format_headers());
    } else if options.show_headers || options.head_only {
        print!("{}", response.format_headers());
    }

    if options.head_only {
        return ExitCode::SUCCESS;
    }

    let output_path = resolve_output(&options);
    write_output(&response.body, output_path.as_deref())
}

fn build_request(url: Url, options: &Options) -> Request {
    let mut request = Request::new(url);

    if let Some(agent) = &options.user_agent {
        request.user_agent = agent.clone();
    }

    if options.head_only {
        request.method = Method::Head;
    }

    if let Some(method) = options.method {
        request.method = method;
    }

    request.headers = options.headers.clone();

    if let Some(user) = &options.user {
        let encoded = base64_encode(user.as_bytes());
        request
            .headers
            .push(("Authorization".into(), format!("Basic {encoded}")));
    }

    if let Some(data) = &options.data {
        request.body = Some(data.as_bytes().to_vec());
        if request.method == Method::Get {
            request.method = Method::Post;
        }
        let has_content_type = request
            .headers
            .iter()
            .any(|(n, _)| n.eq_ignore_ascii_case("content-type"));
        if !has_content_type {
            request.headers.push((
                "Content-Type".into(),
                "application/x-www-form-urlencoded".into(),
            ));
        }
    }

    if let Some(path) = &options.upload_file {
        let data = fs::read(path).unwrap_or_else(|error| {
            eprintln!("wurl: can't read '{path}': {error}");
            std::process::exit(1);
        });
        request.body = Some(data);
        if request.method == Method::Get {
            request.method = Method::Put;
        }
    }

    request
}

fn resolve_output(options: &Options) -> Option<String> {
    if let Some(path) = &options.output {
        return Some(path.clone());
    }

    if options.remote_name {
        let path = options
            .url
            .rsplit('/')
            .next()
            .unwrap_or("download");
        let name = if path.is_empty() { "index.html" } else { path };
        return Some(name.to_string());
    }

    None
}

fn write_output(
    body: &[u8],
    path: Option<&str>,
) -> ExitCode {
    match path {
        Some(path) => match fs::write(path, body) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("wurl: can't write '{path}': {error}");
                ExitCode::FAILURE
            }
        },
        None => {
            io::stdout().write_all(body).ok();
            ExitCode::SUCCESS
        }
    }
}

fn eprint_request(request: &Request) {
    eprintln!(
        "> {} {} HTTP/1.1",
        request.method.as_str(),
        request.url.path
    );
    eprintln!("> Host: {}", request.url.host_header());
    for (name, value) in &request.headers {
        eprintln!("> {name}: {value}");
    }
    eprintln!(">");
}

fn base64_encode(input: &[u8]) -> String {
    const CHARS: &[u8] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrs\
          tuvwxyz0123456789+/";

    let mut result = String::new();
    for chunk in input.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = *chunk.get(1).unwrap_or(&0) as u32;
        let b2 = *chunk.get(2).unwrap_or(&0) as u32;
        let triple = (b0 << 16) | (b1 << 8) | b2;

        result.push(CHARS[(triple >> 18 & 0x3F) as usize] as char);
        result.push(CHARS[(triple >> 12 & 0x3F) as usize] as char);

        if chunk.len() > 1 {
            result.push(CHARS[(triple >> 6 & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }

        if chunk.len() > 2 {
            result.push(CHARS[(triple & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
    }
    result
}

const VERSION: &str = env!("CARGO_PKG_VERSION");

const HELP: &str = "\
Usage: wurl [options...] <url>
 -d, --data <data>          HTTP POST data
 -f, --fail                 Fail with no output on HTTP errors
 -I, --head                 Show document info only
 -H, --header <header>      Pass custom header to server
 -h, --help                 Show this help
 -o, --output <file>        Write to file instead of stdout
 -O, --remote-name          Write output to remote filename
 -i, --show-headers         Show response headers in output
 -s, --silent               Silent mode
 -T, --upload-file <file>   Transfer local file to destination
 -u, --user <user:password> Server user and password
 -A, --user-agent <name>    Send User-Agent to server
 -v, --verbose              Make the operation more talkative
 -V, --version              Show version number and quit
 -X, --request <method>     Specify request method";

fn parse_args() -> Result<Options, String> {
    let args: Vec<String> = std::env::args().skip(1).collect();

    if args.is_empty() {
        println!("{HELP}");
        std::process::exit(0);
    }

    let mut options = Options {
        url: String::new(),
        method: None,
        headers: Vec::new(),
        data: None,
        upload_file: None,
        output: None,
        remote_name: false,
        show_headers: false,
        head_only: false,
        fail_on_error: false,
        silent: false,
        verbose: false,
        user_agent: None,
        user: None,
    };

    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "-h" | "--help" => {
                println!("{HELP}");
                std::process::exit(0);
            }
            "-V" | "--version" => {
                println!("wurl {VERSION}");
                std::process::exit(0);
            }
            "-d" | "--data" => {
                options.data = Some(next_value(&mut iter, arg)?);
            }
            "-H" | "--header" => {
                let header = next_value(&mut iter, arg)?;
                let (name, value) = header
                    .split_once(':')
                    .ok_or("invalid header format, use Name: Value")?;
                options.headers.push((
                    name.trim().to_string(),
                    value.trim().to_string(),
                ));
            }
            "-o" | "--output" => {
                options.output = Some(next_value(&mut iter, arg)?);
            }
            "-T" | "--upload-file" => {
                options.upload_file =
                    Some(next_value(&mut iter, arg)?);
            }
            "-A" | "--user-agent" => {
                options.user_agent =
                    Some(next_value(&mut iter, arg)?);
            }
            "-u" | "--user" => {
                options.user = Some(next_value(&mut iter, arg)?);
            }
            "-X" | "--request" => {
                let method = next_value(&mut iter, arg)?;
                options.method = Some(parse_method(&method)?);
            }
            "-O" | "--remote-name" => {
                options.remote_name = true;
            }
            "-i" | "--show-headers" => {
                options.show_headers = true;
            }
            "-I" | "--head" => {
                options.head_only = true;
            }
            "-f" | "--fail" => {
                options.fail_on_error = true;
            }
            "-s" | "--silent" => {
                options.silent = true;
            }
            "-v" | "--verbose" => {
                options.verbose = true;
            }
            other if other.starts_with('-') => {
                return Err(format!("unknown option: {other}"));
            }
            _ => {
                options.url = arg.clone();
            }
        }
    }

    if options.url.is_empty() {
        return Err("no URL specified".into());
    }

    Ok(options)
}

fn next_value<'a>(
    iter: &mut impl Iterator<Item = &'a String>,
    flag: &str,
) -> Result<String, String> {
    iter.next()
        .cloned()
        .ok_or_else(|| format!("{flag} requires a value"))
}

fn parse_method(input: &str) -> Result<Method, String> {
    match input.to_uppercase().as_str() {
        "GET" => Ok(Method::Get),
        "HEAD" => Ok(Method::Head),
        "POST" => Ok(Method::Post),
        "PUT" => Ok(Method::Put),
        _ => Err(format!("unsupported method: {input}")),
    }
}
