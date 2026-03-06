use std::time::Instant;

fn main() {
    let mut generator = clouded::captcha::CaptchaGenerator::new();
    
    println!("Setting up icon cache...");
    let setup_start = Instant::now();
    if !generator.setup() {
        eprintln!("Failed to setup captcha generator");
        return;
    }
    println!("Setup took: {:?}", setup_start.elapsed());
    
    let crypto = clouded::captcha::CaptchaCrypto::new("test_secret_key");
    let site_key = "test_site";
    
    println!("\nWarming up...");
    for _ in 0..3 {
        clouded::captcha::generate_challenge_with_generator(&crypto, &generator, site_key);
    }
    
    println!("\nBenchmarking 100 generations...");
    let mut times = Vec::new();
    let mut sizes = Vec::new();
    
    for i in 0..100 {
        let start = Instant::now();
        let response = clouded::captcha::generate_challenge_with_generator(
            &crypto,
            &generator,
            site_key
        );
        let elapsed = start.elapsed();
        let size = response.image.len();
        times.push(elapsed);
        sizes.push(size);
        
        if i < 10 || i % 10 == 0 {
            println!("Generation {}: {:?} ({}KB)", i + 1, elapsed, size / 1024);
        }
    }
    
    times.sort();
    sizes.sort();
    let total: std::time::Duration = times.iter().sum();
    let avg = total / times.len() as u32;
    let median = times[times.len() / 2];
    let p95 = times[(times.len() as f64 * 0.95) as usize];
    let min = times[0];
    let max = times[times.len() - 1];
    
    let avg_size = sizes.iter().sum::<usize>() / sizes.len();
    let median_size = sizes[sizes.len() / 2];
    
    println!("\n=== Results ===");
    println!("Min:    {:?}", min);
    println!("Median: {:?}", median);
    println!("Avg:    {:?}", avg);
    println!("P95:    {:?}", p95);
    println!("Max:    {:?}", max);
    println!("\n=== File Sizes ===");
    println!("Avg:    {}KB", avg_size / 1024);
    println!("Median: {}KB", median_size / 1024);
}
