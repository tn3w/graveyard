use rand::Rng;

const TIMESTAMP_JITTER_SECONDS: i64 = 300;
const TIMESTAMP_ROUND_INTERVAL: i64 = 300;

pub fn obfuscate_timestamp(timestamp: i64) -> i64 {
    let mut rng = rand::thread_rng();
    let jitter = rng.gen_range(-TIMESTAMP_JITTER_SECONDS..=TIMESTAMP_JITTER_SECONDS);
    let rounded = (timestamp / TIMESTAMP_ROUND_INTERVAL) * TIMESTAMP_ROUND_INTERVAL;
    rounded + jitter
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_obfuscate_timestamp_adds_jitter() {
        let original = 1640000000;
        let obfuscated = obfuscate_timestamp(original);
        
        let rounded_base = (original / TIMESTAMP_ROUND_INTERVAL) * TIMESTAMP_ROUND_INTERVAL;
        let difference = (obfuscated - rounded_base).abs();
        assert!(difference <= TIMESTAMP_JITTER_SECONDS);
    }

    #[test]
    fn test_obfuscate_timestamp_rounds() {
        let original = 1640000123;
        let obfuscated = obfuscate_timestamp(original);
        
        let rounded_base = (original / TIMESTAMP_ROUND_INTERVAL) * TIMESTAMP_ROUND_INTERVAL;
        let difference = (obfuscated - rounded_base).abs();
        assert!(difference <= TIMESTAMP_JITTER_SECONDS);
    }

    #[test]
    fn test_obfuscate_timestamp_produces_different_values() {
        let original = 1640000000;
        let obfuscated1 = obfuscate_timestamp(original);
        let obfuscated2 = obfuscate_timestamp(original);
        
        assert!(obfuscated1 != obfuscated2 || obfuscated1 == original);
    }
}
