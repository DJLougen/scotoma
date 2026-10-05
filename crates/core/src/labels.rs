//! Maps whatever label vocabulary a model or dataset uses onto our categories.
//! Matching is by keyword so a new HF model usually needs no code change.

use crate::Category;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mapped {
    /// A Safe Harbor identifier: always redacted.
    Phi(Category),
    /// Quasi-identifier (occupation, nationality...): redacted in strict mode only.
    Quasi,
    /// Not an identifier under Safe Harbor (state, country, gender, bare time).
    Keep,
}

/// Strip BIO/BIOES prefixes: "B-first_name" → "first_name".
pub fn strip_prefix(label: &str) -> &str {
    let b = label.as_bytes();
    if b.len() > 2 && (b[1] == b'-' || b[1] == b'_') && matches!(b[0], b'B' | b'I' | b'E' | b'S' | b'L' | b'U') {
        &label[2..]
    } else {
        label
    }
}

pub fn map_label(raw: &str) -> Mapped {
    let l = strip_prefix(raw).to_ascii_lowercase().replace(['-', ' '], "_");
    let has = |k: &str| l.contains(k);
    use Category::*;
    use Mapped::*;

    if l == "o" || l.is_empty() { return Keep; }
    // Scotoma's own category names (used by our benchmark and our models).
    if let Some(cat) = crate::Category::from_tag(&l) {
        return if cat == Org { Quasi } else { Phi(cat) };
    }
    if has("docket") || has("case_number") || has("matter") { return Phi(Id); }
    // Order matters: most specific first.
    if has("email") { return Phi(Email); }
    if has("fax") { return Phi(Fax); }
    if has("phone") || has("telephone") || l == "tel" || has("mobile") { return Phi(Phone); }
    if has("ipv4") || has("ipv6") || l == "ip" || has("ip_address") || l == "ipaddress" { return Phi(Ip); }
    if has("mac_address") || has("device") || has("imei") || has("serial") { return Phi(Device); }
    if has("url") || has("website") || has("http_cookie") { return Phi(Url); }
    if has("ssn") || has("social_security") || has("socialnum") { return Phi(Ssn); }
    // Piiranha's compact vocabulary (TAXNUM, BUILDINGNUM, IDCARDNUM).
    if has("taxnum") || has("idcardnum") { return Phi(Id); }
    if has("buildingnum") { return Phi(Address); }
    // Binary "private vs not" taggers (ai4privacy anonymisers) carry no category;
    // any span they flag is redacted and booked as a generic ID.
    if l == "private" || l == "pii" || l == "sensitive" { return Phi(Id); }
    if has("medical_record") || l == "mrn" || has("patient_id") || l == "medicalrecord" { return Phi(Mrn); }
    if has("health_plan") || has("beneficiary") || has("insurance") || l == "healthplan" { return Phi(Plan); }
    if has("license_plate") || has("vehicle") || l == "vin" || has("vrm") { return Phi(Vehicle); }
    if has("license") || has("licence") || has("certificate") { return Phi(License); }
    if has("biometric") { return Phi(Biometric); }
    if has("date") || l == "dob" || has("birth") { return Phi(Date); }
    if l == "time" { return Keep; }
    if l == "age" { return Phi(Age); }
    if has("postcode") || has("zip") || has("postal") { return Phi(Zip); }
    if has("street") || has("address") || has("building") || has("coordinate") || has("gps") {
        return Phi(Address);
    }
    if l == "state" || l == "country" { return Keep; }
    if has("city") || has("county") || has("location") || l == "loc" || has("hospital") {
        return Phi(Location);
    }
    if has("account") || has("routing") || has("iban") || has("swift") || has("bic")
        || has("credit") || has("card") || l == "cvv" || l == "pin" || has("bitcoin")
        || has("ethereum") || has("litecoin")
    {
        return Phi(Account);
    }
    if has("password") || has("api_key") || has("secret") { return Phi(Id); }
    if has("user_name") || has("username") { return Phi(Id); }
    if has("name") || l == "person" || l == "per" || l == "patient" || l == "doctor" || l == "staff"
        || l == "hcw" || has("private_person")
    {
        return if has("company") || has("organization") || has("organisation") { Quasi } else { Phi(Name) };
    }
    if has("national_id") || has("tax_id") || has("passport") || has("customer_id")
        || has("employee_id") || has("unique_id") || l == "id" || l.ends_with("_id") || has("idnum")
    {
        return Phi(Id);
    }
    if has("org") || has("company") || has("vendor") { return Quasi; }
    if has("occupation") || has("profession") || has("job") || has("nationality")
        || has("religio") || has("political") || has("sexual") || has("ethnic")
        || has("race") || has("marital") || has("education") || has("employment")
        || has("language")
    {
        return Quasi;
    }
    Keep
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn maps_common_vocabularies() {
        assert_eq!(map_label("B-first_name"), Mapped::Phi(Category::Name));
        assert_eq!(map_label("I-medical_record_number"), Mapped::Phi(Category::Mrn));
        assert_eq!(map_label("private_person"), Mapped::Phi(Category::Name));
        assert_eq!(map_label("B-date_of_birth"), Mapped::Phi(Category::Date));
        assert_eq!(map_label("state"), Mapped::Keep);
        assert_eq!(map_label("B-occupation"), Mapped::Quasi);
        assert_eq!(map_label("B-company_name"), Mapped::Quasi);
        assert_eq!(map_label("HOSPITAL"), Mapped::Phi(Category::Location));
        assert_eq!(map_label("B-health_plan_beneficiary_number"), Mapped::Phi(Category::Plan));
        assert_eq!(map_label("S-private_phone"), Mapped::Phi(Category::Phone));
        assert_eq!(map_label("B-PLAN"), Mapped::Phi(Category::Plan));
        assert_eq!(map_label("I-ORG"), Mapped::Quasi);
        assert_eq!(map_label("ZIP"), Mapped::Phi(Category::Zip));
        assert_eq!(map_label("I-SOCIALNUM"), Mapped::Phi(Category::Ssn));
        assert_eq!(map_label("I-TAXNUM"), Mapped::Phi(Category::Id));
        assert_eq!(map_label("I-IDCARDNUM"), Mapped::Phi(Category::Id));
        assert_eq!(map_label("I-BUILDINGNUM"), Mapped::Phi(Category::Address));
        assert_eq!(map_label("B-PRIVATE"), Mapped::Phi(Category::Id));
        assert_eq!(map_label("I-GIVENNAME"), Mapped::Phi(Category::Name));
        assert_eq!(map_label("I-DRIVERLICENSENUM"), Mapped::Phi(Category::License));
    }
}
