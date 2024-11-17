export const config = {
  runtime: 'edge'
};

export default async function handler(request) {
  if (request.method === 'POST') {
    const formData = await request.formData();
    const body = formData.get('Body') || '';
    const from = formData.get('From') || '';
    
    console.log(`Received message: ${body} from ${from}`);
    
    const twiml = `<?xml version="1.0" encoding="UTF-8"?>
                  <Response>
                      <Message>Message received!</Message>
                  </Response>`;
    
    return new Response(twiml, {
      headers: {
        'Content-Type': 'application/xml',
      },
    });
  }
  
  return new Response('{"status":"healthy"}', {
    headers: {
      'Content-Type': 'application/json',
    },
  });
} 