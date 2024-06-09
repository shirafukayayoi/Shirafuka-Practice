const fs = require('fs');
const csv = require('@fast-csv/parse');

const stream = fs.createReadStream('./csv/csvread.csv');

csv.parseStream(stream)
    .on('error', error => console.error(error))
    .on('data', row => console.log(`ROW=${JSON.stringify(row)}`))
    .on('end', rowCount => console.log(`Parsed ${rowCount} rows`));